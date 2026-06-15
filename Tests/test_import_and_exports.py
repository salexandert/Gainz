import datetime
import csv
import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from dateutil.parser import UnknownTimezoneWarning
from openpyxl import load_workbook

from app import create_app
from app.extensions import db
from app.import_transactions import routes as import_routes
from app.import_transactions.routes import (
    _manual_batch_rows,
    _manual_row_is_blank,
    _manual_transaction_from_values,
    _public_import_result,
    _remove_data_source,
)
from app.services.audit_packet_service import AuditPacketService
from app.services.import_service import ImportService
from app.services.import_warning_service import import_warning_review_rows
from transaction import Buy, Sell, Send
from transactions import Transactions
from utils import (
    get_audit_readiness_summary,
    get_form_8949_report_rows,
    get_form_8949_table_data,
    get_form_8949_totals,
)
from configs.config import config_dict
from werkzeug.datastructures import MultiDict


def empty_transactions():
    transactions = Transactions.__new__(Transactions)
    transactions.revision_num = 0
    transactions.saves = []
    transactions.index = 0
    transactions.conversions = []
    transactions.asset_objects = []
    transactions.import_warnings = []
    transactions.import_warning_reviews = []
    transactions.basis_review_notes = []
    transactions.tax_year_records = []
    transactions.tax_evidence_records = []
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

    def test_import_page_get_does_not_build_heavy_unused_tables(self):
        transactions = empty_transactions()
        transactions.saves = [{
            "value": "C:/Development/Gainz/saves/saved_test.xlsx",
            "description": "Current test save",
            "revision_num": 7,
            "modified_time": 1710000000,
        }]
        transactions.view = transactions.saves[0]["value"]

        app = create_app(config_dict["Debug"], selenium=True)
        app.config.update(
            WTF_CSRF_ENABLED=False,
            transactions=transactions,
            UPLOAD_FOLDER="uploads",
        )

        with app.test_request_context("/import_transactions/"):
            with patch.object(import_routes, "render_template", return_value="ok") as render_mock:
                with patch.object(import_routes, "get_stats_table_data", side_effect=AssertionError("unused")):
                    with patch.object(import_routes, "get_all_trans_table_data", side_effect=AssertionError("unused")):
                        with patch.object(transactions, "load_saves", side_effect=AssertionError("unused")):
                            response = import_routes.import_wizard.__wrapped__()

        self.assertEqual("ok", response)
        context = render_mock.call_args.kwargs
        self.assertNotIn("stats_table_data", context)
        self.assertNotIn("transactions", context)
        self.assertEqual(7, context["save_summary"]["revision"])

    def test_import_page_renders_manual_batch_table(self):
        app = create_app(config_dict["Debug"], selenium=True)
        app.config.update(WTF_CSRF_ENABLED=False)

        with app.test_request_context("/import_transactions/#manual-transactions"):
            rendered_page = app.jinja_env.get_template(
                "import_transactions.html"
            ).render(
                manual_trans=import_routes.ManualTransaction(),
                current_holdings=import_routes.CurrentHoldings(),
                save_summary={
                    "revision": 0,
                    "save_count": 0,
                    "recent_saves": [],
                },
                data_summary={
                    "transaction_count": 0,
                    "asset_count": 0,
                    "source_count": 0,
                    "link_count": 0,
                    "sources": [],
                    "import_warnings": [],
                    "import_warning_rows": [],
                    "type_counts": {},
                },
            )

        self.assertIn('id="manual_transactions_table"', rendered_page)
        self.assertIn('name="manual_type[]"', rendered_page)
        self.assertIn('name="manual_batch_submit"', rendered_page)
        self.assertIn("Blank rows are ignored", rendered_page)

    def test_import_page_renders_import_warning_workflow(self):
        app = create_app(config_dict["Debug"], selenium=True)
        app.config.update(WTF_CSRF_ENABLED=False)
        warnings = [
            "Skipped row 12 from coinbase.csv: unrecognized transaction type 'Mystery Reward'"
        ]

        with app.test_request_context("/import_transactions/"):
            rendered_page = app.jinja_env.get_template(
                "import_transactions.html"
            ).render(
                manual_trans=import_routes.ManualTransaction(),
                current_holdings=import_routes.CurrentHoldings(),
                save_summary={
                    "revision": 0,
                    "save_count": 0,
                    "recent_saves": [],
                },
                data_summary={
                    "transaction_count": 0,
                    "asset_count": 0,
                    "source_count": 0,
                    "link_count": 0,
                    "sources": [],
                    "import_warnings": warnings,
                    "import_warning_rows": import_warning_review_rows(warnings),
                    "type_counts": {},
                },
            )

        self.assertIn('id="import_warning_workflow"', rendered_page)
        self.assertIn("Import warnings need review", rendered_page)
        self.assertIn("coinbase.csv", rendered_page)
        self.assertIn("Suggested next action", rendered_page)

    def test_import_page_renders_column_review_workflow(self):
        app = create_app(config_dict["Debug"], selenium=True)
        app.config.update(WTF_CSRF_ENABLED=False)

        with app.test_request_context("/import_transactions/"):
            rendered_page = app.jinja_env.get_template(
                "import_transactions.html"
            ).render(
                manual_trans=import_routes.ManualTransaction(),
                current_holdings=import_routes.CurrentHoldings(),
                save_summary={
                    "revision": 0,
                    "save_count": 0,
                    "recent_saves": [],
                },
                data_summary={
                    "transaction_count": 0,
                    "asset_count": 0,
                    "source_count": 0,
                    "link_count": 0,
                    "sources": [],
                    "import_warnings": [],
                    "import_warning_rows": [],
                    "type_counts": {},
                },
            )

        self.assertIn('id="import_column_mapper"', rendered_page)
        self.assertIn("Column review needed", rendered_page)
        self.assertIn("Choose Header And Columns", rendered_page)

    def test_public_import_result_strips_server_paths(self):
        result = _public_import_result({
            "file_path": r"C:\private\uploads\transactions.csv",
            "imported_count": 1,
            "warnings": [
                "Skipped row 12 from transactions.csv: unrecognized transaction type 'Mystery Reward'"
            ],
            "files": [
                {
                    "file_path": r"C:\private\demo_data\cash_app_sample.csv",
                    "imported_count": 3,
                }
            ],
        })

        self.assertNotIn("file_path", result)
        self.assertEqual("transactions.csv", result["filename"])
        self.assertNotIn("file_path", result["files"][0])
        self.assertEqual("cash_app_sample.csv", result["files"][0]["filename"])
        self.assertEqual("transactions.csv", result["warning_rows"][0]["source"])
        self.assertEqual("12", result["warning_rows"][0]["row"])

    def test_public_mapping_prompt_does_not_create_warning_rows(self):
        result = _public_import_result({
            "file_path": r"C:\private\uploads\cash_app_report.csv",
            "imported_count": 0,
            "skipped_count": 0,
            "warnings": [
                "Column review needed. Gainz could not confidently identify the required import columns."
            ],
            "mapping_required": True,
        })

        self.assertEqual("cash_app_report.csv", result["filename"])
        self.assertEqual([], result["warning_rows"])

    def test_import_route_errors_do_not_expose_exception_details(self):
        app = create_app(config_dict["Debug"], selenium=True)
        app.config.update(
            WTF_CSRF_ENABLED=False,
            transactions=empty_transactions(),
            UPLOAD_FOLDER="uploads",
        )

        with app.test_request_context("/import_transactions/demo", method="POST"):
            with patch.object(
                import_routes.ImportService,
                "import_demo_data",
                side_effect=RuntimeError(r"C:\private\secret.csv"),
            ):
                response, status_code = import_routes.import_demo_data.__wrapped__()

        data = response.get_json()
        self.assertEqual(400, status_code)
        self.assertIn("could not complete", data["error"])
        self.assertNotIn("secret.csv", data["error"])
        self.assertNotIn("C:\\", data["error"])

    def test_manual_batch_rows_skip_blanks_and_build_transactions(self):
        form_data = MultiDict([
            ("manual_type[]", "buy"),
            ("manual_timestamp[]", "2024-01-01T09:30"),
            ("manual_symbol[]", "btc"),
            ("manual_quantity[]", "0.25"),
            ("manual_usd_spot[]", "42000"),
            ("manual_type[]", "sell"),
            ("manual_timestamp[]", "2024-02-02T10:45"),
            ("manual_symbol[]", "ETH"),
            ("manual_quantity[]", "1.5"),
            ("manual_usd_spot[]", "2500"),
            ("manual_type[]", "buy"),
            ("manual_timestamp[]", ""),
            ("manual_symbol[]", ""),
            ("manual_quantity[]", ""),
            ("manual_usd_spot[]", ""),
        ])

        rows = [
            row
            for row in _manual_batch_rows(form_data)
            if not _manual_row_is_blank(row)
        ]
        transactions = [
            _manual_transaction_from_values(row, index + 1)
            for index, row in enumerate(rows)
        ]

        self.assertEqual(2, len(transactions))
        self.assertIsInstance(transactions[0], Buy)
        self.assertIsInstance(transactions[1], Sell)
        self.assertEqual("BTC", transactions[0].symbol)
        self.assertEqual(0.25, transactions[0].quantity)
        self.assertEqual(2500, transactions[1].usd_spot)
        self.assertEqual("Gainz App Manual Add", transactions[1].source)

    def test_manual_batch_rejects_partial_rows(self):
        with self.assertRaisesRegex(ValueError, "Row 3: complete USD Spot"):
            _manual_transaction_from_values(
                {
                    "type": "buy",
                    "timestamp": "2024-01-01T09:30",
                    "symbol": "BTC",
                    "quantity": "0.5",
                    "usd_spot": "",
                },
                row_number=3,
            )

    def test_import_page_posts_manual_batch_as_one_revision(self):
        transactions = empty_transactions()
        saved_descriptions = []
        transactions.save = lambda description=None: saved_descriptions.append(description)
        app = create_app(config_dict["Debug"], selenium=True)
        app.config.update(
            WTF_CSRF_ENABLED=False,
            transactions=transactions,
            UPLOAD_FOLDER="uploads",
        )

        form_data = {
            "manual_batch_submit": "1",
            "manual_type[]": ["buy", "sell", "buy"],
            "manual_timestamp[]": ["2024-01-01T09:30", "2024-02-02T10:45", ""],
            "manual_symbol[]": ["BTC", "ETH", ""],
            "manual_quantity[]": ["0.25", "1.5", ""],
            "manual_usd_spot[]": ["42000", "2500", ""],
        }

        with app.test_request_context(
            "/import_transactions/",
            method="POST",
            data=form_data,
        ):
            response = import_routes.import_wizard.__wrapped__()

        self.assertEqual(302, response.status_code)
        self.assertIn("manual_added=2", response.location)
        self.assertEqual(["Manually Added 2 Transactions"], saved_descriptions)
        self.assertEqual(["buy", "sell"], [t.trans_type for t in transactions.transactions])
        self.assertEqual(["BTC", "ETH"], [t.symbol for t in transactions.transactions])

    def test_remove_data_source_removes_transactions_and_cleans_links(self):
        transactions = empty_transactions()
        removed_buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "remove.csv")
        remaining_buy = Buy("BTC", 2, datetime.datetime(2024, 1, 2), 100, "keep.csv")
        remaining_sell = Sell("BTC", 0.5, datetime.datetime(2024, 2, 1), 300, "keep.csv")
        remaining_sell.link_transaction(removed_buy, 0.5)
        transactions.transactions = [removed_buy, remaining_buy, remaining_sell]
        transactions.import_warnings = [
            "Skipped row 4 from remove.csv: unrecognized transaction type 'Mystery'",
            "Skipped row 6 from remove.csv: unrecognized transaction type 'Other'",
            "Skipped row 5 from keep.csv: unrecognized transaction type 'Mystery'",
        ]
        transactions.set_import_warning_review(
            "Skipped row 4 from remove.csv: unrecognized transaction type 'Mystery'",
            decision="note",
            note="Reviewed before source cleanup.",
        )

        result = _remove_data_source(transactions, "remove.csv")

        self.assertEqual(1, result["removed_count"])
        self.assertEqual(["keep.csv", "keep.csv"], [transaction.source for transaction in transactions.transactions])
        self.assertEqual([], remaining_sell.links)
        self.assertEqual([], remaining_sell.linked_transactions)
        self.assertEqual([
            "Skipped row 5 from keep.csv: unrecognized transaction type 'Mystery'"
        ], transactions.import_warnings)
        self.assertEqual(
            "Reviewed before source cleanup.",
            transactions.get_import_warning_review(
                "Skipped row 4 from remove.csv: unrecognized transaction type 'Mystery'"
            )["note"],
        )
        self.assertEqual(
            "cleared_by_source_update",
            transactions.get_import_warning_review(
                "Skipped row 6 from remove.csv: unrecognized transaction type 'Other'"
            )["decision"],
        )

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

    def test_import_service_imports_gdax_fills(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "trade id,product,side,created at,size,size unit,price,fee,total,price/fee/total unit",
            "1,BTC-USD,BUY,2024-01-05T10:15:00Z,0.1,BTC,40000,1,4000,USD",
            "2,BTC-USD,SELL,2024-02-05T10:15:00Z,0.05,BTC,50000,1,2500,USD",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "gdax_fills.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(2, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual(["buy", "sell"], [t.trans_type for t in transactions.transactions])
        self.assertEqual({"BTC"}, transactions.assets)
        self.assertEqual([0.1, 0.05], sorted([t.quantity for t in transactions.transactions], reverse=True))

    def test_import_service_imports_cash_app_with_updated_headers(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Reference ID,Transaction Date,Activity,Fiat Currency,USD Amount,Network Fee,Crypto,Spot Price USD,Crypto Quantity",
            "cash-new-001,2024-01-05 10:15:00 PST,Bitcoin Purchase,USD,-$1000.00,$0.00,Bitcoin,\"$40,000.00\",0.025 BTC",
            "cash-new-002,2024-08-20 14:00:00 PDT,Bitcoin Sale,USD,$1200.00,-$12.00,Bitcoin,\"$60,000.00\",0.020 BTC",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "cash_app_updated.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(2, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(["buy", "sell"], [t.trans_type for t in transactions.transactions])
        self.assertEqual(["BTC", "BTC"], [t.symbol for t in transactions.transactions])

    def test_import_service_imports_coinbase_with_updated_headers(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Trade ID,Date UTC,Activity Type,Asset Symbol,Amount Transacted,Unit Price,Total Amount,Memo",
            "cb-new-001,2023-01-10 12:00:00 UTC,Purchased,ETH,2.0,$1200.00,$2400.00,Bought 2 ETH",
            "cb-new-002,2024-03-20 12:00:00 UTC,Sold,ETH,-1.5,$3000.00,$4500.00,Sold 1.5 ETH",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "coinbase_updated.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(2, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(["buy", "sell"], [t.trans_type for t in transactions.transactions])
        self.assertEqual([2.0, 1.5], [t.quantity for t in transactions.transactions])

    def test_import_service_imports_coinbase_earn_as_receive(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Timestamp,Transaction Type,Asset,Quantity Transacted,Total Inclusive of Fees and Spread,Notes",
            "2024-02-01 09:00:00 UTC,Coinbase Earn,SOL,3.5,$35.00,Earned SOL",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "coinbase_earn.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(1, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual([], result["warnings"])
        self.assertEqual("receive", transactions.transactions[0].trans_type)
        self.assertEqual("SOL", transactions.transactions[0].symbol)
        self.assertEqual(10.0, transactions.transactions[0].usd_spot)

    def test_import_service_imports_generic_alias_csv(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Created At,Operation,Token Symbol,Token Quantity,Transaction Value",
            "2024-02-01 09:00:00 UTC,Receive,SOL,3.5,$350.00",
            "2024-02-15 09:00:00 UTC,Send,SOL,1.0,$125.00",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "wallet_export.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(2, result["imported_count"])
        self.assertEqual(0, result["skipped_count"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(["receive", "send"], [t.trans_type for t in transactions.transactions])
        self.assertEqual([100.0, 125.0], [t.usd_spot for t in transactions.transactions])

    def test_import_service_handles_eastern_timezone_abbreviations_without_warning(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Created At,Operation,Token Symbol,Token Quantity,Transaction Value",
            "2019-02-01 09:00:00 EST,Receive,BTC,0.1,$350.00",
            "2019-08-15 14:30:00 EDT,Send,BTC,0.05,$250.00",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "wallet_export_eastern_time.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        unknown_timezone_warnings = [
            warning for warning in caught
            if issubclass(warning.category, UnknownTimezoneWarning)
        ]
        self.assertEqual([], unknown_timezone_warnings)
        self.assertEqual(2, result["imported_count"])
        self.assertEqual(["receive", "send"], [t.trans_type for t in transactions.transactions])

    def test_import_service_finds_header_row_after_preamble(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Wallet Export",
            "Generated for demo testing",
            "Created At,Operation,Token Symbol,Token Quantity,Transaction Value",
            "2024-02-01 09:00:00 UTC,Receive,SOL,3.5,$350.00",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "wallet_export_with_preamble.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(1, result["imported_count"])
        self.assertEqual(3, result["header_row_used"])
        self.assertEqual("SOL", transactions.transactions[0].symbol)

    def test_import_service_can_pause_for_column_review(self):
        transactions = empty_transactions()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path("demo_data/cash_app_sample.csv")
            result = ImportService(temp_dir).import_upload(
                FileUpload(source),
                transactions,
                review_columns=True,
            )

        self.assertTrue(result["mapping_required"])
        self.assertEqual(0, result["imported_count"])
        self.assertEqual([], transactions.transactions)
        self.assertEqual(1, result["mapping"]["header_row"])
        self.assertEqual(2, result["mapping"]["data_start_row"])
        self.assertTrue(result["mapping"]["sample_rows"])

    def test_import_service_requests_mapping_when_pricing_column_missing(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Created At,Operation,Token Symbol,Token Quantity",
            "2024-02-01 09:00:00 UTC,Receive,SOL,3.5",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "wallet_export_without_usd.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertTrue(result["mapping_required"])
        self.assertIn("USD", result["warnings"][0])
        self.assertEqual(0, result["imported_count"])
        self.assertEqual([], transactions.transactions)

    def test_import_service_imports_mapped_csv_with_later_data_start_row(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Wallet Export",
            "Generated for demo testing",
            "Created At,Operation,Token Symbol,Token Quantity,Transaction Value",
            "Notes: internal transfers included below,,,,",
            "2024-02-01 09:00:00 UTC,Receive,SOL,3.5,$350.00",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "wallet_export_with_note_row.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            service = ImportService(upload_dir)
            upload_result = service.import_upload(FileUpload(source), transactions, review_columns=True)
            mapped_result = service.import_mapped_file(
                upload_result["file_path"],
                transactions,
                header_row=3,
                data_start_row=5,
                column_mapping={
                    "date": "Created At",
                    "transaction_type": "Operation",
                    "asset_type": "Token Symbol",
                    "asset_amount": "Token Quantity",
                    "fiat_amount": "Transaction Value",
                },
            )

        self.assertEqual(1, mapped_result["imported_count"])
        self.assertEqual([], mapped_result["warnings"])
        self.assertEqual("SOL", transactions.transactions[0].symbol)
        self.assertEqual("receive", transactions.transactions[0].trans_type)
        self.assertEqual(100.0, transactions.transactions[0].usd_spot)

    def test_import_warnings_do_not_expose_parser_exception_details(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "Created At,Operation,Token Symbol,Token Quantity,Transaction Value",
            "not a date,Receive,SOL,3.5,$350.00",
            "2024-02-15 09:00:00 UTC,Send,SOL,1.0,$125.00",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "wallet_export_bad_row.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            result = ImportService(upload_dir).import_upload(FileUpload(source), transactions)

        self.assertEqual(1, result["imported_count"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertIn("could not parse this row", warning)
        self.assertIn("wallet_export_bad_row.csv", warning)
        self.assertNotIn("Unknown string format", warning)
        self.assertNotIn("not a date", warning)
        self.assertNotIn(str(source.parent), warning)

    def test_import_service_returns_mapping_prompt_for_unknown_columns(self):
        transactions = empty_transactions()
        csv_text = "\n".join([
            "When,Kind,Thing,Units,Value",
            "2024-02-01 09:00:00 UTC,Acquire,SOL,3.5,$350.00",
        ])

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "unknown_columns.csv"
            upload_dir = Path(temp_dir) / "uploads"
            source.write_text(csv_text, encoding="utf-8")
            service = ImportService(upload_dir)
            result = service.import_upload(FileUpload(source), transactions)

            self.assertTrue(result["mapping_required"])
            mapped_result = service.import_mapped_file(
                result["file_path"],
                transactions,
                header_row=1,
                column_mapping={
                    "date": "When",
                    "transaction_type": "Kind",
                    "asset_type": "Thing",
                    "asset_amount": "Units",
                    "fiat_amount": "Value",
                },
            )

        self.assertEqual(1, mapped_result["imported_count"])
        self.assertEqual([], mapped_result["warnings"])
        self.assertEqual("buy", transactions.transactions[0].trans_type)
        self.assertEqual(100.0, transactions.transactions[0].usd_spot)

    def test_demo_data_golden_form_8949_totals_after_fifo_linking(self):
        transactions = empty_transactions()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = ImportService(temp_dir).import_demo_data(transactions, repo_root=Path.cwd())

        self.assertEqual(8, result["imported_count"])
        self.assertEqual([], result["warnings"])
        self.assertEqual([], transactions.auto_link(asset=None, algo="fifo"))

        totals = get_form_8949_totals(transactions)
        self.assertEqual(1, totals["short"]["rows"])
        self.assertEqual(2000.0, totals["short"]["proceeds"])
        self.assertEqual(600.0, totals["short"]["cost_basis"])
        self.assertEqual(1400.0, totals["short"]["gain_loss"])
        self.assertEqual(2, totals["long"]["rows"])
        self.assertEqual(5700.0, totals["long"]["proceeds"])
        self.assertEqual(3800.0, totals["long"]["cost_basis"])
        self.assertEqual(1900.0, totals["long"]["gain_loss"])
        self.assertEqual(3, totals["total"]["rows"])
        self.assertEqual(7700.0, totals["total"]["proceeds"])
        self.assertEqual(4400.0, totals["total"]["cost_basis"])
        self.assertEqual(3300.0, totals["total"]["gain_loss"])

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

    def test_export_handles_timezone_aware_imported_datetimes(self):
        transactions = empty_transactions()
        buy = Buy(
            "ETH",
            1,
            datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            100,
            "coinbase",
        )
        sell = Sell(
            "ETH",
            1,
            datetime.datetime(2024, 6, 1, tzinfo=datetime.timezone.utc),
            300,
            "coinbase",
        )
        sell.link_transaction(buy, 1)
        transactions.transactions = [buy, sell]

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = transactions.export_to_excel(output_dir=temp_dir)
            workbook = load_workbook(export_path, data_only=False)
            sheet = workbook["2024 8949 Short"]

            self.assertIsNone(sheet["B2"].value.tzinfo)
            self.assertIsNone(sheet["C2"].value.tzinfo)

    def test_holdings_classifies_documented_sends_and_runs_fifo(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 2, datetime.datetime(2024, 1, 1), 100, "demo")
        send = Send("BTC", 1, datetime.datetime(2024, 6, 1), 200, "wallet")
        transactions.transactions = [buy, send]
        transactions.set_holdings("BTC", 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            class RouteTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"

            app = create_app(RouteTestConfig, selenium=True)
            app.config["transactions"] = transactions

            with app.test_client() as client:
                response = client.post(
                    "/holdings_accounting/sends_to_sells",
                    json={
                        "asset": ["BTC"],
                        "quantity": "1",
                        "auto_link": True,
                    },
                )

            self.assertEqual(200, response.status_code)
            payload = response.get_json()
            sells = [trans for trans in transactions if trans.trans_type == "sell"]
            sends = [trans for trans in transactions if trans.trans_type == "send"]

            self.assertIn("taxable disposal", payload["message"])
            self.assertEqual(1, payload["links_created"])
            self.assertEqual([], payload["auto_link_failures"])
            self.assertEqual(1, len(sells))
            self.assertEqual(0, len(sends))
            self.assertEqual(1, len(sells[0].links))
            self.assertEqual("0", payload["difference_breakdown"]["summary"]["difference"])

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_bulk_holdings_sets_primary_asset_and_zeroes_others(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "demo"),
            Buy("ETH", 2, datetime.datetime(2024, 1, 2), 50, "demo"),
            Buy("BCH", 3, datetime.datetime(2024, 1, 3), 25, "demo"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            class RouteTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"

            app = create_app(RouteTestConfig, selenium=True)
            app.config["transactions"] = transactions

            with app.test_client() as client:
                response = client.post(
                    "/holdings_accounting/bulk_holdings",
                    json={
                        "primary_asset": "BTC",
                        "primary_quantity": "0.12345678",
                    },
                )

            self.assertEqual(200, response.status_code)
            payload = response.get_json()
            self.assertEqual("0.12345678", payload["primary_quantity"])
            self.assertEqual(0.12345678, transactions.get_holdings("BTC"))
            self.assertEqual(0, transactions.get_holdings("ETH"))
            self.assertEqual(0, transactions.get_holdings("BCH"))
            self.assertEqual(["BCH", "ETH"], payload["zeroed_assets"])

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_data_source_summary_flags_likely_full_history_overlap(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Buy("BCH", 1, datetime.datetime(2024, 1, 1), 100, "exchange_all_activity.csv"),
            Sell("BCH", 0.5, datetime.datetime(2024, 2, 1), 200, "exchange_all_activity.csv"),
            Buy("BCH", 1, datetime.datetime(2024, 1, 1), 100, "exchange_all_activity_2025.csv"),
            Sell("BCH", 0.5, datetime.datetime(2024, 2, 1), 200, "exchange_all_activity_2025.csv"),
        ]

        summary = import_routes._data_source_summary(transactions)

        self.assertEqual(1, summary["source_overlap_count"])
        self.assertEqual("Likely full-history overlap", summary["source_overlaps"][0]["status"])
        self.assertEqual(
            {"Potential overlap"},
            {source["status"] for source in summary["sources"]},
        )

    def test_audit_readiness_surfaces_source_overlap_review(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange_all_activity.csv"),
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange_all_activity_2025.csv"),
        ]
        transactions.set_holdings("BTC", 2)

        readiness = get_audit_readiness_summary(transactions)

        self.assertFalse(readiness["is_ready"])
        self.assertEqual(1, readiness["metrics"]["source_overlaps"])
        self.assertTrue(any("overlapping source file" in warning for warning in readiness["warnings"]))
        self.assertEqual(1, len(readiness["missing_records"]["source_overlaps"]))
        self.assertTrue(any(group["key"] == "source_overlaps" for group in readiness["blocker_groups"]))
        source_group = next(group for group in readiness["blocker_groups"] if group["key"] == "source_overlaps")
        self.assertEqual("Review sources", source_group["action_label"])

    def test_audit_readiness_prioritizes_holdings_before_basis_review(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange"),
            Sell("BTC", 0.5, datetime.datetime(2024, 2, 1), 150, "exchange"),
        ]

        readiness = get_audit_readiness_summary(transactions)

        self.assertFalse(readiness["is_ready"])
        self.assertEqual("holdings", readiness["blocker_groups"][0]["key"])
        self.assertEqual("Enter holdings", readiness["primary_action"]["label"])
        self.assertIn("Declare current holdings", readiness["next_action"])
        self.assertTrue(readiness["missing_records"]["basis_summary"])

    def test_leave_basis_unresolved_keeps_export_not_ready_with_research_status(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Sell("LTC", 1, datetime.datetime(2019, 1, 7), 40, "exchange"),
        ]
        transactions.set_holdings("LTC", 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            class RouteTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"

            app = create_app(RouteTestConfig, selenium=True)
            app.config["transactions"] = transactions

            with app.test_client() as client:
                response = client.post(
                    "/holdings_accounting/leave_basis_unresolved",
                    json={
                        "asset": ["LTC"],
                        "note": "User will investigate source records later.",
                    },
                )

            self.assertEqual(200, response.status_code)
            payload = response.get_json()
            self.assertIn("needs user research", payload["message"])
            self.assertEqual(
                "User will investigate source records later.",
                transactions.get_basis_review_note("LTC")["note"],
            )

            readiness = get_audit_readiness_summary(transactions)
            self.assertFalse(readiness["is_ready"])
            self.assertEqual("Needs user research", readiness["missing_records"]["basis"][0]["status"])
            self.assertTrue(
                any("Missing basis left as needs user research" in blocker for blocker in readiness["blockers"])
            )
            basis_group = next(group for group in readiness["blocker_groups"] if group["key"] == "missing_basis")
            self.assertEqual("Needs research", basis_group["status"])
            self.assertEqual("/holdings_accounting/", basis_group["action_url"])

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_tax_filing_review_confirms_suggested_totals_or_marks_research(self):
        transactions = empty_transactions()
        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_path = Path(temp_dir) / "2024_crypto_tax_workbook.csv"
            evidence_path.write_text(
                "Year,Reported Proceeds,Reported Cost Basis,Reported Gain Loss,Tax Paid\n"
                "2024,300,100,200,25\n",
                encoding="utf-8",
            )
            transactions.set_tax_evidence_record(
                year=2024,
                evidence_type="crypto_workbook",
                evidence_label=evidence_path.name,
                evidence_path=str(evidence_path),
            )

            class RouteTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"

            app = create_app(RouteTestConfig, selenium=True)
            app.config["transactions"] = transactions

            with app.test_client() as client:
                confirm_response = client.post(
                    "/tax_filing_review/suggested_totals/confirm",
                    data={
                        "year": "2024",
                        "reported_proceeds": "300",
                        "reported_cost_basis": "100",
                        "reported_gain_loss": "200",
                        "tax_paid": "25",
                        "source_reference": evidence_path.name,
                        "notes": "Reviewed source row.",
                    },
                )
                research_response = client.post(
                    "/tax_filing_review/suggested_totals/research",
                    data={
                        "year": "2023",
                        "source_reference": "2023 filed return PDF",
                        "notes": "Needs source review.",
                    },
                )

            self.assertEqual(302, confirm_response.status_code)
            self.assertEqual(302, research_response.status_code)
            confirmed = transactions.get_tax_year_record(2024)
            self.assertEqual(300.0, confirmed["reported_proceeds"])
            self.assertEqual(25.0, confirmed["tax_paid"])
            self.assertIn("Confirmed from Gainz", confirmed["notes"])
            needs_research = transactions.get_tax_year_record(2023)
            self.assertEqual("Needs research", needs_research["filing_status"])
            self.assertEqual("Needs source review.", needs_research["notes"])

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_tax_filing_review_imports_filed_totals_csv_with_unicode_hyphen_headers(self):
        transactions = empty_transactions()
        csv_text = (
            "Tax Year,Short\u2011term Proceeds,Short\u2011term Cost Basis,Short\u2011term Gain,"
            "Long\u2011term Proceeds,Long\u2011term Cost Basis,Long\u2011term Gain\n"
            "2021,$0.00,$0.00,$0.00,$0.00,$0.00,$0.00\n"
            "2022,\"$18,338.19\",\"$18,453.11\",($114.93),\"$112,689.71\",\"$51,005.76\",\"$61,683.96\"\n"
            "missing,,,,,,\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            class RouteTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"

            app = create_app(RouteTestConfig, selenium=True)
            app.config["transactions"] = transactions

            with app.test_client() as client:
                response = client.post(
                    "/tax_filing_review/import_csv",
                    data={
                        "csv_file": (
                            io.BytesIO(csv_text.encode("utf-8")),
                            "filed_totals.csv",
                        ),
                    },
                    content_type="multipart/form-data",
                )

            self.assertEqual(302, response.status_code)
            self.assertIn("imported_tax_rows=2", response.location)
            self.assertIn("skipped_tax_rows=1", response.location)
            zero_record = transactions.get_tax_year_record(2021)
            self.assertEqual(0.0, zero_record["reported_gain_loss"])
            record = transactions.get_tax_year_record(2022)
            self.assertEqual(131027.90, round(record["reported_proceeds"], 2))
            self.assertEqual(69458.87, round(record["reported_cost_basis"], 2))
            self.assertEqual(61569.03, round(record["reported_gain_loss"], 2))
            self.assertIsNone(record["tax_paid"])
            self.assertEqual(
                {2021, 2022},
                {record["year"] for record in transactions.tax_evidence_records},
            )

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_export_routes_use_requested_output_folder(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "demo")
        sell = Sell("BTC", 1, datetime.datetime(2024, 6, 1), 300, "demo")
        sell.link_transaction(buy, 1)
        transactions.transactions = [buy, sell]
        transactions.set_holdings("BTC", 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "tax-review-output"

            class ExportRouteTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                EXPORT_FOLDER = str(Path(temp_dir) / "default-exports")
                AUDIT_PACKET_FOLDER = str(Path(temp_dir) / "default-packets")

            app = create_app(ExportRouteTestConfig, selenium=True)
            app.config["transactions"] = transactions

            with app.test_client() as client:
                export_response = client.post(
                    "/export/save",
                    json={"output_dir": str(output_dir)},
                )
                packet_response = client.post(
                    "/export/audit_packet",
                    json={"output_dir": str(output_dir)},
                )

            export_payload = export_response.get_json()
            packet_payload = packet_response.get_json()

            self.assertEqual(200, export_response.status_code)
            self.assertEqual(200, packet_response.status_code)
            self.assertEqual(output_dir.resolve(), Path(export_payload["output_dir"]))
            self.assertEqual(output_dir.resolve(), Path(packet_payload["output_dir"]))
            self.assertEqual(output_dir.resolve(), Path(export_payload["path"]).parent)
            self.assertEqual(output_dir.resolve(), Path(packet_payload["path"]).parent)
            self.assertTrue(Path(export_payload["path"]).exists())
            self.assertTrue((Path(packet_payload["path"]) / "03_manifests" / "audit_packet_summary.json").exists())

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_form_8949_rows_are_built_from_links_with_prorated_fees(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 2, datetime.datetime(2024, 1, 1), 100, "buy-source")
        buy.fee = 10.0
        sell = Sell("BTC", 1, datetime.datetime(2024, 6, 1), 300, "sell-source")
        sell.fee = 6.0
        sell.link_transaction(buy, 1)
        transactions.transactions = [buy, sell]

        rows = get_form_8949_report_rows(transactions, asset="BTC", term="short")
        table_rows = get_form_8949_table_data(transactions, asset="BTC", term="short")
        totals = get_form_8949_totals(transactions)

        self.assertEqual(1, len(rows))
        self.assertEqual("short", rows[0]["term"])
        self.assertEqual(294, rows[0]["proceeds"])
        self.assertEqual(105, rows[0]["cost_basis"])
        self.assertEqual(189, rows[0]["gain_loss"])
        self.assertEqual("$294.00", table_rows[0][3])
        self.assertEqual("$105.00", table_rows[0][4])
        self.assertEqual("$189.00", table_rows[0][5])
        self.assertEqual(294, totals["short"]["proceeds"])
        self.assertEqual(189, totals["total"]["gain_loss"])

    def test_audit_packet_service_creates_manifest_and_report(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "demo_data/cash_app_sample.csv")
        sell = Sell("BTC", 1, datetime.datetime(2024, 6, 1), 300, "demo_data/cash_app_sample.csv")
        sell.link_transaction(buy, 1)
        transactions.transactions = [buy, sell]
        transactions.set_holdings("BTC", 0)
        transactions.import_warnings = ["Example warning"]
        transactions.set_tax_year_record(
            2024,
            reported_proceeds=300,
            reported_cost_basis=100,
            reported_gain_loss=200,
            tax_paid=25,
            evidence_reference="2024 filed return",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            tax_evidence_path = Path(temp_dir) / "2024_crypto_tax_workbook.csv"
            tax_evidence_path.write_text(
                "Year,Reported Proceeds,Reported Cost Basis,Reported Gain Loss,Tax Paid\n"
                "2024,300,100,200,25\n",
                encoding="utf-8",
            )
            transactions.set_tax_evidence_record(
                year=2024,
                evidence_type="crypto_workbook",
                evidence_label=tax_evidence_path.name,
                evidence_path=str(tax_evidence_path),
            )
            packet_root = Path(temp_dir) / "packets"
            export_root = Path(temp_dir) / "exports"
            packet_path = Path(AuditPacketService(packet_root, export_root).create_packet(transactions))

            self.assertTrue((packet_path / "00_memos" / "METHODOLOGY.md").exists())
            self.assertTrue((packet_path / "03_manifests" / "evidence_manifest.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "form_8949_short_term.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "form_8949_totals.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "holdings_reconciliation.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "current_holdings_lots.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "import_warnings.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "source_overlap_review.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "tax_filing_alignment.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "tax_evidence_inventory.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "tax_evidence_items.csv").exists())
            self.assertTrue((packet_path / "01_reports" / "suggested_filed_totals.csv").exists())
            self.assertTrue((packet_path / "03_manifests" / "tax_evidence_inventory.json").exists())
            self.assertTrue((packet_path / "03_manifests" / "suggested_filed_totals.json").exists())
            self.assertEqual(1, len(list((packet_path / "01_reports").glob("*.xlsx"))))
            self.assertEqual(1, len(list((packet_path / "02_source_files").glob("*.csv"))))

            with open(packet_path / "01_reports" / "import_warnings.csv", newline="", encoding="utf-8") as file:
                warning_rows = list(csv.DictReader(file))
            self.assertEqual("Example warning", warning_rows[0]["warning"])
            self.assertEqual("Active", warning_rows[0]["active_status"])
            self.assertEqual("Needs review", warning_rows[0]["status"])

            with open(packet_path / "01_reports" / "form_8949_totals.csv", newline="", encoding="utf-8") as file:
                totals = {row["term"]: row for row in csv.DictReader(file)}
            self.assertEqual("300.00", totals["short"]["proceeds"])
            self.assertEqual("200.00", totals["total"]["gain_loss"])

            with open(packet_path / "01_reports" / "holdings_reconciliation.csv", newline="", encoding="utf-8") as file:
                holdings_rows = list(csv.DictReader(file))
            self.assertEqual("BTC", holdings_rows[0]["asset"])
            self.assertEqual("Verified", holdings_rows[0]["status"])

            with open(packet_path / "01_reports" / "tax_filing_alignment.csv", newline="", encoding="utf-8") as file:
                tax_alignment_rows = list(csv.DictReader(file))
            self.assertEqual("2024", tax_alignment_rows[0]["year"])
            self.assertEqual("Aligned", tax_alignment_rows[0]["status"])
            self.assertEqual("25.00", tax_alignment_rows[0]["tax_paid"])

            with open(packet_path / "01_reports" / "suggested_filed_totals.csv", newline="", encoding="utf-8") as file:
                suggested_rows = list(csv.DictReader(file))
            self.assertEqual("2024", suggested_rows[0]["year"])
            self.assertEqual("High", suggested_rows[0]["confidence"])
            self.assertEqual("200.00", suggested_rows[0]["reported_gain_loss"])

            summary = json.loads((packet_path / "03_manifests" / "audit_packet_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(200, summary["form_8949_totals"]["total"]["gain_loss"])
            self.assertEqual(1, summary["import_warning_count"])
            self.assertEqual("Aligned", summary["tax_filing_alignment"]["overall_status"])
            self.assertIn("tax_evidence_inventory", summary)
            self.assertEqual(1, len(summary["suggested_filed_totals"]))

    def test_audit_packet_preserves_cleared_import_warning_review_records(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "demo_data/cash_app_sample.csv")
        transactions.transactions = [buy]
        transactions.set_holdings("BTC", 1)
        warning = "Imported row 10 from sample.csv with $0 USD spot price."
        transactions.set_import_warning_review(
            warning,
            decision="true_zero_value_transfer",
            note="Reviewed before warning was cleared.",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            packet_root = Path(temp_dir) / "packets"
            export_root = Path(temp_dir) / "exports"
            packet_path = Path(AuditPacketService(packet_root, export_root).create_packet(transactions))

            with open(packet_path / "01_reports" / "import_warnings.csv", newline="", encoding="utf-8") as file:
                warning_rows = list(csv.DictReader(file))

            self.assertEqual(1, len(warning_rows))
            self.assertEqual("Cleared from active warnings", warning_rows[0]["active_status"])
            self.assertEqual("True zero-value transfer", warning_rows[0]["decision"])
            self.assertEqual("Reviewed before warning was cleared.", warning_rows[0]["note"])

            summary = json.loads((packet_path / "03_manifests" / "audit_packet_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(0, summary["import_warning_count"])
            self.assertEqual(1, summary["import_warning_review_count"])


if __name__ == "__main__":
    unittest.main()
