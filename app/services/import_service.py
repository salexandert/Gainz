import copy
import json
import os
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

from app.services.import_warning_service import clear_import_warnings_for_source
from date_parsing import parse_gainz_datetime
from parsers import (
    analyze_csv_import,
    import_transactions,
    normalize_asset_symbol,
    parse_quantity_value,
    standardize_transaction_type,
)
from runtime_paths import resource_dir


class ImportService:
    DEMO_FILES = [
        "cash_app_sample.csv",
        "coinbase_sample.csv",
        "coinbase_convert_sample.csv",
    ]
    MISSING_BASIS_DEMO_FILES = [
        "coinbase_partial_basis_fee_sample.csv",
    ]

    def __init__(self, upload_folder):
        self.upload_folder = upload_folder

    def import_upload(self, file_storage, transactions, review_columns=False):
        filename = secure_filename(file_storage.filename)
        if not filename:
            raise ValueError("Upload is missing a filename.")

        os.makedirs(self.upload_folder, exist_ok=True)
        file_path = os.path.join(self.upload_folder, filename)

        file_storage.save(file_path)
        if not filename.lower().endswith(".csv"):
            warning = "Gainz currently imports CSV files. Export or save this file as CSV and try again."
            clear_import_warnings_for_source(transactions, filename)
            transactions.last_import_result = {
                "file_path": file_path,
                "imported_count": 0,
                "skipped_count": 0,
                "warnings": [warning],
            }
            transactions.import_warnings = getattr(transactions, "import_warnings", []) + [warning]
            return {
                "file_path": file_path,
                "imported_count": 0,
                "skipped_count": 0,
                "warnings": [warning],
            }

        analysis = self.analyze_import_file(file_path)
        if analysis.get("detected_format") in {"coinbase_raw", "ledger_live"}:
            return self._native_preview_required_result(file_path, analysis)
        if review_columns:
            return self._mapping_required_result(
                file_path,
                analysis,
                "Review the detected header row, first data row, and column choices before importing.",
            )

        if not analysis["can_import"]:
            return self._mapping_required_result(file_path, analysis)

        if not analysis["has_pricing"]:
            return self._mapping_required_result(
                file_path,
                analysis,
                (
                    "Column review needed. Gainz found transaction columns but not a "
                    "USD spot price or total USD value column. Map a USD value column "
                    "before importing."
                ),
            )

        result = self._transactional_import(
            file_path,
            transactions,
            header_row=analysis["header_row"],
            data_start_row=analysis["data_start_row"],
        )
        return {
            **result,
            "header_row_used": analysis["header_row"],
            "data_start_row_used": analysis["data_start_row"],
            "import_preview": analysis.get("import_preview", {}),
        }

    def import_mapped_file(self, file_path, transactions, header_row, column_mapping, data_start_row=None):
        analysis = self.analyze_import_file(
            file_path,
            header_row=header_row,
            column_mapping=column_mapping,
            data_start_row=data_start_row,
        )
        if not analysis["can_import"]:
            return self._mapping_required_result(file_path, analysis)

        result = self._transactional_import(
            file_path,
            transactions,
            header_row=header_row,
            column_mapping=column_mapping,
            data_start_row=analysis["data_start_row"],
        )
        return {
            **result,
            "header_row_used": int(header_row or 1),
            "data_start_row_used": analysis["data_start_row"],
            "import_preview": analysis.get("import_preview", {}),
        }

    def import_native_file(self, file_path, transactions, header_row=1, data_start_row=None):
        analysis = self.analyze_import_file(
            file_path,
            header_row=header_row,
            data_start_row=data_start_row,
        )
        rows = analysis.get("_normalized_rows") or []
        return self._transactional_import(
            file_path,
            transactions,
            header_row=analysis.get("header_row", header_row),
            data_start_row=analysis.get("data_start_row", data_start_row),
            prepared_rows=rows,
            prepared_format=analysis.get("detected_format"),
            expected_output_rows=(analysis.get("import_preview") or {}).get("output_rows"),
        )

    def import_native_payload(self, payload_path, transactions):
        payload_path = Path(payload_path)
        if not payload_path.is_file():
            raise ValueError("The reviewed import preview expired. Upload the source CSV again.")

        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        source_path = Path(payload.get("source_path") or "")
        try:
            if not source_path.is_file():
                raise ValueError("The reviewed source file is no longer available. Upload it again.")
            from parsers import _file_sha256

            if _file_sha256(source_path) != payload.get("source_sha256"):
                raise ValueError("The source CSV changed after preview. Upload and review it again.")
            return self._transactional_import(
                str(source_path),
                transactions,
                header_row=payload.get("header_row", 1),
                data_start_row=payload.get("data_start_row", 2),
                prepared_rows=payload.get("rows") or [],
                prepared_format=payload.get("detected_format"),
                expected_output_rows=payload.get("expected_output_rows"),
            )
        finally:
            payload_path.unlink(missing_ok=True)

    def analyze_import_file(self, file_path, header_row=None, column_mapping=None, data_start_row=None):
        if not str(file_path).lower().endswith(".csv"):
            return {
                "can_import": False,
                "has_pricing": False,
                "header_row": 1,
                "data_start_row": 2,
                "columns": [],
                "suggested_mapping": {},
                "mapping_fields": [],
                "missing_required": ["date", "transaction_type", "asset_type", "asset_amount"],
                "header_candidates": [],
                "sample_rows": [],
            }

        return analyze_csv_import(
            file_path,
            header_row=header_row,
            column_mapping=column_mapping,
            data_start_row=data_start_row,
        )

    def import_demo_data(self, transactions, repo_root=None):
        return self._import_demo_files(
            transactions,
            self.DEMO_FILES,
            repo_root=repo_root,
            demo_kind="basic",
        )

    def import_missing_basis_demo(self, transactions, repo_root=None):
        result = self._import_demo_files(
            transactions,
            self.MISSING_BASIS_DEMO_FILES,
            repo_root=repo_root,
            demo_kind="missing_basis",
        )
        result["demo_profile"] = {
            "name": "Missing-basis professional review",
            "asset": "BCH",
            "declared_holdings": "0",
            "guidance": (
                "Next: declare BCH holdings as 0, then continue to Reconcile to review "
                "the partially supported sale and its professional treatment options."
            ),
        }
        return result

    def _import_demo_files(self, transactions, demo_files, repo_root=None, demo_kind="basic"):
        repo_root = Path(repo_root) if repo_root else resource_dir()
        demo_root = repo_root / "demo_data"
        results = []
        total_imported = 0
        total_skipped = 0
        warnings = []

        for demo_file in demo_files:
            source = demo_root / demo_file
            import_result = self._transactional_import(str(source), transactions)
            imported_count = import_result.get("imported_count", 0)
            skipped_count = import_result.get("skipped_count", 0)
            result_warnings = import_result.get("warnings", [])
            results.append({
                "file_path": str(source),
                "filename": demo_file,
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "warnings": result_warnings,
            })
            total_imported += imported_count
            total_skipped += skipped_count
            warnings.extend(result_warnings)

        return {
            "imported_count": total_imported,
            "skipped_count": total_skipped,
            "warnings": warnings,
            "files": results,
            "demo": True,
            "demo_kind": demo_kind,
        }

    def _mapping_required_result(self, file_path, analysis, message=None):
        return {
            "file_path": file_path,
            "imported_count": 0,
            "skipped_count": 0,
            "warnings": [
                message or (
                    "Column review needed. Gainz could not confidently identify the "
                    "required import columns. Choose the header row and map the "
                    "columns below."
                )
            ],
            "mapping_required": True,
            "mapping": analysis,
        }

    def _native_preview_required_result(self, file_path, analysis):
        payload_path = self._write_native_payload(file_path, analysis)
        return {
            "file_path": file_path,
            "imported_count": 0,
            "skipped_count": 0,
            "warnings": [],
            "native_preview_required": True,
            "detected_format": analysis.get("detected_format"),
            "header_row": analysis.get("header_row", 1),
            "data_start_row": analysis.get("data_start_row", 2),
            "import_preview": analysis.get("import_preview", {}),
            "_prepared_payload_path": str(payload_path),
        }

    def _write_native_payload(self, file_path, analysis):
        os.makedirs(self.upload_folder, exist_ok=True)
        payload_path = Path(self.upload_folder) / f".gainz-import-preview-{uuid.uuid4().hex}.json"
        payload = {
            "source_path": str(Path(file_path).resolve()),
            "source_sha256": analysis.get("_source_sha256"),
            "detected_format": analysis.get("detected_format"),
            "header_row": analysis.get("header_row", 1),
            "data_start_row": analysis.get("data_start_row", 2),
            "expected_output_rows": (analysis.get("import_preview") or {}).get("output_rows", 0),
            "rows": analysis.get("_normalized_rows") or [],
        }
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=True, default=str, allow_nan=False),
            encoding="utf-8",
        )
        return payload_path

    def _transactional_import(
        self,
        file_path,
        transactions,
        *,
        header_row=1,
        column_mapping=None,
        data_start_row=None,
        prepared_rows=None,
        prepared_format=None,
        expected_output_rows=None,
    ):
        """Stage an import and publish it only when the normalized rows commit cleanly."""
        if prepared_rows is not None:
            preflight_error = self._prepared_rows_preflight_error(prepared_rows)
            if preflight_error:
                result = self._source_failure_result(
                    file_path,
                    expected_output_rows,
                    preflight_error,
                )
                transactions.last_import_result = result
                return result

        staged = copy.copy(transactions)
        staged.transactions = list(getattr(transactions, "transactions", []) or [])
        staged.import_warnings = list(getattr(transactions, "import_warnings", []) or [])
        staged.import_warning_reviews = list(
            getattr(transactions, "import_warning_reviews", []) or []
        )
        staged.import_receipts = list(getattr(transactions, "import_receipts", []) or [])
        staged.last_import_result = dict(getattr(transactions, "last_import_result", {}) or {})
        staged.save = lambda description=None: None

        clear_import_warnings_for_source(staged, file_path)
        imported_count, skipped_count = import_transactions(
            file_path,
            staged,
            header_row=header_row,
            column_mapping=column_mapping,
            data_start_row=data_start_row,
            prepared_rows=prepared_rows,
            prepared_format=prepared_format,
        )
        staged_result = dict(getattr(staged, "last_import_result", {}) or {})
        skipped_rows = staged_result.get("skipped_rows", []) or []
        fatal_rows = [row for row in skipped_rows if row.get("affects_calculations")]
        duplicate_rows = [
            row for row in skipped_rows
            if str(row.get("reason") or "").startswith("Duplicate or companion-source")
        ]
        committed_or_duplicate = imported_count + len(duplicate_rows)
        preview_mismatch = (
            expected_output_rows is not None
            and committed_or_duplicate != int(expected_output_rows)
        )
        zero_row_failure = (
            imported_count == 0
            and not duplicate_rows
            and (fatal_rows or staged_result.get("warnings"))
        )

        strict_preview_failure = prepared_rows is not None and (fatal_rows or preview_mismatch)
        if strict_preview_failure or zero_row_failure:
            detail = (
                "The reviewed preview could not be committed without parse or row-count differences."
                if strict_preview_failure
                else "The source did not produce any valid transactions."
            )
            result = self._source_failure_result(
                file_path,
                expected_output_rows,
                detail,
            )
            transactions.last_import_result = result
            return result

        for attribute in (
            "transactions",
            "import_warnings",
            "import_warning_reviews",
            "import_receipts",
            "last_import_result",
        ):
            setattr(transactions, attribute, getattr(staged, attribute))

        if imported_count:
            transactions.save(description=f"Imported from {os.path.basename(str(file_path))}")

        result = dict(getattr(transactions, "last_import_result", {}) or {})
        result.setdefault("file_path", str(file_path))
        result.setdefault("imported_count", imported_count)
        result.setdefault("skipped_count", skipped_count)
        result["transactional_commit"] = True
        result["rollback_complete"] = False
        return result

    @staticmethod
    def _prepared_rows_preflight_error(rows):
        for index, row in enumerate(rows, start=1):
            if str(row.get("Skip Reason") or "").strip():
                continue
            source_row = row.get("Source Row") or index
            asset = normalize_asset_symbol(row.get("Asset Type"))
            transaction_type = standardize_transaction_type(row.get("Transaction Type"))
            quantity = abs(parse_quantity_value(row.get("Asset Amount")))
            if not asset:
                return f"Reviewed row {source_row} has no crypto asset."
            if transaction_type not in {"Buy", "Sell", "Send", "Receive"}:
                return f"Reviewed row {source_row} has unsupported type '{row.get('Transaction Type')}'."
            if quantity <= 0:
                return f"Reviewed row {source_row} has no positive asset quantity."
            try:
                parse_gainz_datetime(row.get("Date"))
            except (TypeError, ValueError, OverflowError):
                return f"Reviewed row {source_row} has an invalid date/time value."
        return ""

    @staticmethod
    def _source_failure_result(file_path, expected_output_rows, detail):
        source_name = os.path.basename(str(file_path))
        warning = (
            f"Gainz did not import {source_name}. {detail} No transactions, row warnings, "
            "or revision were saved. Review the source format and retry."
        )
        return {
            "file_path": str(file_path),
            "imported_count": 0,
            "skipped_count": 0,
            "warnings": [warning],
            "source_failure": True,
            "rollback_complete": True,
            "persistent_warnings_added": 0,
            "expected_output_rows": expected_output_rows,
        }
