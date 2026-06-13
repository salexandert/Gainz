import os
from pathlib import Path

from werkzeug.utils import secure_filename

from app.services.import_warning_service import clear_import_warnings_for_source
from parsers import analyze_csv_import, import_transactions


class ImportService:
    DEMO_FILES = [
        "cash_app_sample.csv",
        "coinbase_sample.csv",
        "coinbase_convert_sample.csv",
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
        if review_columns:
            return self._mapping_required_result(
                file_path,
                analysis,
                "Review the detected header row, first data row, and column choices before importing.",
            )

        if not analysis["can_import"]:
            return self._mapping_required_result(file_path, analysis)

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
            "header_row_used": analysis["header_row"],
            "data_start_row_used": analysis["data_start_row"],
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
            "header_row_used": int(header_row or 1),
            "data_start_row_used": analysis["data_start_row"],
        }

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
        repo_root = Path(repo_root or Path(__file__).resolve().parents[2])
        demo_root = repo_root / "demo_data"
        results = []
        total_imported = 0
        total_skipped = 0
        warnings = []

        for demo_file in self.DEMO_FILES:
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
        }

    def _mapping_required_result(self, file_path, analysis, message=None):
        return {
            "file_path": file_path,
            "imported_count": 0,
            "skipped_count": 0,
            "warnings": [
                message or "Gainz could not identify the required import columns. Choose the header row and map the columns below."
            ],
            "mapping_required": True,
            "mapping": analysis,
        }
