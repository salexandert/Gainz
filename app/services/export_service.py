class ExportService:
    def __init__(self, export_folder=None):
        self.export_folder = export_folder

    def export_to_excel(self, transactions, readiness=None):
        return transactions.export_to_excel(
            output_dir=self.export_folder,
            readiness=readiness,
        )
