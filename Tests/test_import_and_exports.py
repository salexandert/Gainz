import datetime
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from app.services.audit_packet_service import AuditPacketService
from app.services.import_service import ImportService
from transaction import Buy, Sell
from transactions import Transactions


def empty_transactions():
    transactions = Transactions.__new__(Transactions)
    transactions.revision_num = 0
    transactions.saves = []
    transactions.index = 0
    transactions.conversions = []
    transactions.asset_objects = []
    transactions.view = ""
    transactions.transactions = []
    transactions.save = lambda description=None: None
    return transactions


class FileUpload:
    def __init__(self, source):
        self.source = Path(source)
        self.filename = self.source.name

    def save(self, destination):
        Path(destination).write_bytes(self.source.read_bytes())


class ImportAndExportTests(unittest.TestCase):
    def test_import_service_imports_cash_app_sample(self):
        transactions = empty_transactions()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path("demo_data/cash_app_sample.csv")
            result = ImportService(temp_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(3, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual(["buy", "buy", "sell"], [t.trans_type for t in transactions.transactions])
        self.assertEqual({"BTC"}, transactions.assets)

    def test_import_service_imports_coinbase_sample(self):
        transactions = empty_transactions()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path("demo_data/coinbase_sample.csv")
            result = ImportService(temp_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(3, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual(["buy", "buy", "sell"], [t.trans_type for t in transactions.transactions])
        self.assertEqual({"ETH"}, transactions.assets)

    def test_import_service_imports_coinbase_convert_as_sell_and_buy(self):
        transactions = empty_transactions()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path("demo_data/coinbase_convert_sample.csv")
            result = ImportService(temp_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(2, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual([], result["warnings"])
        self.assertEqual([], getattr(transactions, "import_warnings", []))

        self.assertEqual(["sell", "buy"], [t.trans_type for t in transactions.transactions])
        self.assertEqual(["ETH", "BTC"], [t.symbol for t in transactions.transactions])
        self.assertEqual([0.5, 0.02], [t.quantity for t in transactions.transactions])
        self.assertEqual(4000, transactions.transactions[0].usd_spot)
        self.assertEqual(100000, transactions.transactions[1].usd_spot)

    def test_export_includes_8949_short_totals(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "demo")
        sell = Sell("BTC", 1, datetime.datetime(2024, 6, 1), 300, "demo")
        sell.link_transaction(buy, 1)
        transactions.transactions = [buy, sell]

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = transactions.export_to_excel(output_dir=temp_dir)
            workbook = load_workbook(export_path, data_only=False)
            sheet = workbook["2024 8949 Short"]

            self.assertEqual("Crypto BTC", sheet["A2"].value)
            self.assertEqual(300, sheet["D2"].value)
            self.assertEqual(100, sheet["E2"].value)
            self.assertEqual(200, sheet["H2"].value)

    def test_audit_packet_service_creates_manifest_and_report(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "demo_data/cash_app_sample.csv")
        sell = Sell("BTC", 1, datetime.datetime(2024, 6, 1), 300, "demo_data/cash_app_sample.csv")
        sell.link_transaction(buy, 1)
        transactions.transactions = [buy, sell]

        with tempfile.TemporaryDirectory() as temp_dir:
            packet_root = Path(temp_dir) / "packets"
            export_root = Path(temp_dir) / "exports"
            packet_path = Path(AuditPacketService(packet_root, export_root).create_packet(transactions))

            self.assertTrue((packet_path / "00_memos" / "METHODOLOGY.md").exists())
            self.assertTrue((packet_path / "03_manifests" / "evidence_manifest.csv").exists())
            self.assertEqual(1, len(list((packet_path / "01_reports").glob("*.xlsx"))))
            self.assertEqual(1, len(list((packet_path / "02_source_files").glob("*.csv"))))


if __name__ == "__main__":
    unittest.main()
