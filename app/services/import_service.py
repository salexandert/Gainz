import os
from pathlib import Path

from werkzeug.utils import secure_filename

from app.services.import_warning_service import clear_import_warnings_for_source
from parsers import analyze_csv_import, import_transactions
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
        if analysis.get("detected_format") == "coinbase_raw":
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

        clear_import_warnings_for_source(transactions, filename)
        imported_count, skipped_count = import_transactions(
            file_path,
            transactions,
            header_row=analysis["header_row"],
            data_start_row=analysis["data_start_row"],
        )

        return {
            "file_path": file_path,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "warnings": getattr(transactions, "last_import_result", {}).get("warnings", []),
            "skipped_rows": getattr(transactions, "last_import_result", {}).get("skipped_rows", []),
            "integrity_checks": getattr(transactions, "last_import_result", {}).get("integrity_checks", []),
            "import_receipts": getattr(transactions, "last_import_result", {}).get("import_receipts", []),
            "input_reliability_failed": getattr(transactions, "last_import_result", {}).get(
                "input_reliability_failed",
                False,
            ),
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

        clear_import_warnings_for_source(transactions, file_path)
        imported_count, skipped_count = import_transactions(
            file_path,
            transactions,
            header_row=header_row,
            column_mapping=column_mapping,
            data_start_row=analysis["data_start_row"],
        )

        return {
            "file_path": file_path,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "warnings": getattr(transactions, "last_import_result", {}).get("warnings", []),
            "skipped_rows": getattr(transactions, "last_import_result", {}).get("skipped_rows", []),
            "integrity_checks": getattr(transactions, "last_import_result", {}).get("integrity_checks", []),
            "import_receipts": getattr(transactions, "last_import_result", {}).get("import_receipts", []),
            "input_reliability_failed": getattr(transactions, "last_import_result", {}).get(
                "input_reliability_failed",
                False,
            ),
            "header_row_used": int(header_row or 1),
            "data_start_row_used": analysis["data_start_row"],
            "import_preview": analysis.get("import_preview", {}),
        }

    def import_native_file(self, file_path, transactions, header_row=1, data_start_row=None):
        return self.import_mapped_file(
            file_path,
            transactions,
            header_row=header_row,
            column_mapping={},
            data_start_row=data_start_row,
        )

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
            clear_import_warnings_for_source(transactions, demo_file)
            imported_count, skipped_count = import_transactions(str(source), transactions)
            result_warnings = getattr(transactions, "last_import_result", {}).get("warnings", [])
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
        }
