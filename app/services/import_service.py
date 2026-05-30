import os

from werkzeug.utils import secure_filename

from parsers import import_transactions


class ImportService:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder

    def import_upload(self, file_storage, transactions):
        filename = secure_filename(file_storage.filename)
        if not filename:
            raise ValueError("Upload is missing a filename.")

        os.makedirs(self.upload_folder, exist_ok=True)
        file_path = os.path.join(self.upload_folder, filename)

        file_storage.save(file_path)
        imported_count, skipped_count = import_transactions(file_path, transactions)

        return {
            "file_path": file_path,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "warnings": getattr(transactions, "last_import_result", {}).get("warnings", []),
        }
