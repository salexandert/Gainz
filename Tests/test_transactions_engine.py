import datetime
import os
import tempfile
import unittest
from pathlib import Path

import transactions as transactions_module
from app.auto_link.routes import _preview_auto_link_failures
from app.model.routes import _model_sale_payload
from app.stats.routes import _auto_fix_safe_issues
from openpyxl import Workbook
from transaction import Buy, Receive, Sell, Send
from transactions import Transactions
from utils import (
    get_audit_readiness_summary,
    get_current_holdings_lot_table_data,
    get_holdings_difference_breakdown,
    get_multi_asset_holdings_reconciliation_table_data,
    get_unrealized_chart_data,
)


def empty_transactions():
    transactions = Transactions.__new__(Transactions)
    transactions.revision_num = 0
    transactions.saves = []
    transactions.index = 0
    transactions.conversions = []
    transactions.asset_objects = []
    transactions.import_warnings = []
    transactions.view = ""
    transactions.transactions = []
    transactions.saved_descriptions = []

    def fake_save(description=None):
        transactions.saved_descriptions.append(description)

    transactions.save = fake_save
    return transactions


class TransactionsEngineTests(unittest.TestCase):
    def test_default_load_uses_most_recent_save_not_highest_revision(self):
        original_basedir = transactions_module.basedir
        original_load = Transactions.load

        def write_save(path, revision_num):
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Description"
            sheet.cell(row=1, column=1, value=path.stem)
            sheet.cell(row=1, column=2, value=revision_num)
            workbook.save(path)
            workbook.close()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            saves_dir = temp_path / "saves"
            saves_dir.mkdir()

            older = saves_dir / "saved_older_high_revision.xlsx"
            newer = saves_dir / "saved_newer_low_revision.xlsx"
            write_save(older, 1000)
            write_save(newer, 1)
            os.utime(older, (100, 100))
            os.utime(newer, (200, 200))

            loaded_paths = []

            def fake_load(self, filename):
                loaded_paths.append(Path(filename).name)
                return []

            try:
                transactions_module.basedir = str(temp_path)
                Transactions.load = fake_load

                transactions = Transactions()
            finally:
                transactions_module.basedir = original_basedir
                Transactions.load = original_load

        self.assertEqual("saved_newer_low_revision.xlsx", Path(transactions.view).name)
        self.assertEqual(["saved_newer_low_revision.xlsx"], loaded_paths)

    def test_assets_excludes_fiat_symbols_but_keeps_transactions(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Receive("USD", 100, datetime.datetime(2024, 1, 1), "cash", 1),
            Buy("BTC", 1, datetime.datetime(2024, 1, 2), 100, "exchange"),
        ]

        self.assertEqual({"BTC"}, transactions.assets)
        self.assertEqual(2, len(transactions.transactions))

    def test_current_holdings_lots_show_remaining_basis_by_acquisition_date(self):
        transactions = empty_transactions()
        first_buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange")
        second_buy = Buy("BTC", 2, datetime.datetime(2024, 2, 1), 200, "exchange")
        sell = Sell("BTC", 0.4, datetime.datetime(2024, 3, 1), 300, "exchange")
        sell.link_transaction(first_buy, 0.4)
        transactions.transactions = [first_buy, second_buy, sell]

        lots = get_current_holdings_lot_table_data(transactions, "BTC")

        self.assertEqual(2, len(lots))
        self.assertEqual("2024-01-01 00:00:00", lots[0][2])
        self.assertEqual("0.6", lots[0][3])
        self.assertEqual("$60.00", lots[0][6])
        self.assertEqual("2024-02-01 00:00:00", lots[1][2])
        self.assertEqual("2", lots[1][3])
        self.assertEqual("$400.00", lots[1][6])

    def test_current_holdings_lots_include_receives_and_ignore_fiat(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Receive("ETH", 3, datetime.datetime(2024, 1, 1), "wallet", 50),
            Receive("USD", 100, datetime.datetime(2024, 1, 2), "cash", 1),
        ]

        lots = get_current_holdings_lot_table_data(transactions)

        self.assertEqual(1, len(lots))
        self.assertEqual("ETH", lots[0][0])
        self.assertEqual("Receive", lots[0][1])
        self.assertEqual("$150.00", lots[0][6])

    def test_declared_holdings_allocates_current_holdings_to_newest_available_lots(self):
        transactions = empty_transactions()
        transactions.set_holdings("BTC", 0.5)
        transactions.transactions = [
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "old"),
            Buy("BTC", 2, datetime.datetime(2024, 2, 1), 200, "new"),
        ]

        lots = get_current_holdings_lot_table_data(transactions, "BTC")

        self.assertEqual(1, len(lots))
        self.assertEqual("2024-02-01 00:00:00", lots[0][2])
        self.assertEqual("0.5", lots[0][3])
        self.assertEqual("$100.00", lots[0][6])

    def test_unrealized_chart_data_uses_current_lots_and_usd_spot(self):
        transactions = empty_transactions()
        first_buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange")
        second_buy = Buy("BTC", 2, datetime.datetime(2024, 2, 1), 200, "exchange")
        sell = Sell("BTC", 0.4, datetime.datetime(2024, 3, 1), 300, "exchange")
        sell.link_transaction(first_buy, 0.4)
        transactions.transactions = [first_buy, second_buy, sell]

        chart = get_unrealized_chart_data(transactions, "BTC", 300)

        self.assertEqual(300, chart["current_usd_spot"])
        self.assertEqual(2, len(chart["points"]))
        self.assertEqual("2024-01-01 00:00:00", chart["points"][0]["x"])
        self.assertEqual(120, chart["points"][0]["y"])
        self.assertEqual("$60.00", chart["points"][0]["cost_basis"])
        self.assertEqual("$180.00", chart["points"][0]["current_value"])
        self.assertEqual(200, chart["points"][1]["y"])

    def test_multi_asset_holdings_reconciliation_includes_all_crypto_assets(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange"),
            Sell("BTC", 0.25, datetime.datetime(2024, 2, 1), 200, "exchange"),
            Receive("ETH", 2, datetime.datetime(2024, 1, 1), "wallet", 50),
            Receive("USD", 100, datetime.datetime(2024, 1, 2), "cash", 1),
        ]
        transactions.transactions[1].link_transaction(transactions.transactions[0], 0.25)
        transactions.set_holdings("BTC", 0.75)

        rows = get_multi_asset_holdings_reconciliation_table_data(transactions)

        self.assertEqual(["BTC", "ETH"], [row[0] for row in rows])
        self.assertEqual("0.75", rows[0][1])
        self.assertEqual("0.75", rows[0][2])
        self.assertEqual("0", rows[0][5])
        self.assertEqual("Verified", rows[0][6])
        self.assertEqual("N/A", rows[1][1])
        self.assertEqual("Needs declared holdings", rows[1][6])

    def test_holdings_difference_breakdown_explains_running_timeline(self):
        transactions = empty_transactions()
        transactions.set_holdings("BTC", 0.5)
        transactions.transactions = [
            Buy("BTC", 2, datetime.datetime(2024, 1, 1), 100, "C:\\private\\coinbase.csv"),
            Sell("BTC", 0.25, datetime.datetime(2024, 2, 1), 200, "C:\\private\\coinbase.csv"),
            Send("BTC", 0.75, datetime.datetime(2024, 3, 1), 250, "C:\\private\\cash_app.csv"),
            Receive("BTC", 0.1, datetime.datetime(2025, 1, 1), "wallet.csv", 300),
        ]

        breakdown = get_holdings_difference_breakdown(transactions, "BTC")

        self.assertEqual("1.75", breakdown["summary"]["expected_holdings"])
        self.assertEqual("1.25", breakdown["summary"]["difference"])
        self.assertEqual("1.1", breakdown["summary"]["imported_net"])
        self.assertIn("Buys 2 - sells 0.25 = 1.75 BTC", breakdown["summary"]["expected_formula"])
        self.assertIn("Expected 1.75 - declared 0.5 = 1.25 BTC", breakdown["summary"]["difference_formula"])
        self.assertEqual([
            "2024",
            3,
            "2",
            "0.25",
            "0.75",
            "0",
            "1.75",
            "1.75",
            "1",
            "1",
        ], breakdown["yearly_rows"][0])
        self.assertEqual([
            "2025",
            1,
            "0",
            "0",
            "0",
            "0.1",
            "0",
            "1.75",
            "0.1",
            "1.1",
        ], breakdown["yearly_rows"][1])
        self.assertEqual(4, len(breakdown["transaction_rows"]))
        self.assertEqual("coinbase.csv", breakdown["transaction_rows"][0][9])
        self.assertEqual("0", breakdown["transaction_rows"][2][5])
        self.assertEqual("-0.75", breakdown["transaction_rows"][2][7])
        self.assertEqual("1", breakdown["transaction_rows"][2][8])

    def test_auto_link_preview_reports_failures_without_creating_links(self):
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "test")
        covered_sell = Sell("BTC", 0.5, datetime.datetime(2024, 2, 1), 300, "test")
        early_sell = Sell("BTC", 0.5, datetime.datetime(2023, 12, 1), 300, "test")

        covered_failures = _preview_auto_link_failures("BTC", [buy], [covered_sell], "fifo")
        early_failures = _preview_auto_link_failures("BTC", [buy], [early_sell], "fifo")

        self.assertEqual([], covered_failures)
        self.assertEqual(0, len(buy.links))
        self.assertEqual(0, len(covered_sell.links))
        self.assertEqual(1, len(early_failures))
        self.assertEqual(0.5, early_failures[0]["unlinkable"])

    def test_set_holdings_creates_and_updates_asset_record(self):
        transactions = empty_transactions()

        transactions.set_holdings("btc", 0.5)
        transactions.set_holdings("BTC", 0.75)

        self.assertEqual(1, len(transactions.asset_objects))
        self.assertEqual("BTC", transactions.asset_objects[0].symbol)
        self.assertEqual(0.75, transactions.get_holdings("BTC"))

    def test_audit_readiness_flags_missing_links_and_holdings(self):
        transactions = empty_transactions()
        transactions.transactions = [
            Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange"),
            Sell("BTC", 1, datetime.datetime(2024, 2, 1), 200, "exchange"),
        ]

        readiness = get_audit_readiness_summary(transactions)

        self.assertFalse(readiness["is_ready"])
        self.assertEqual("Not ready", readiness["status"])
        self.assertEqual(1, readiness["metrics"]["assets_with_unlinked_sales"])
        self.assertEqual(1, readiness["metrics"]["assets_needing_holdings"])
        self.assertEqual(0, readiness["metrics"]["form_8949_rows"])
        self.assertTrue(any("Review or create basis links" in blocker for blocker in readiness["blockers"]))

    def test_audit_readiness_is_ready_when_links_and_holdings_match(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "exchange")
        sell = Sell("BTC", 0.25, datetime.datetime(2024, 6, 1), 300, "exchange")
        sell.link_transaction(buy, 0.25)
        transactions.transactions = [buy, sell]
        transactions.set_holdings("BTC", 0.75)

        readiness = get_audit_readiness_summary(transactions)

        self.assertTrue(readiness["is_ready"])
        self.assertEqual("Ready for review", readiness["status"])
        self.assertEqual(1, readiness["metrics"]["form_8949_rows"])
        self.assertEqual("$75.00", readiness["metrics"]["form_8949_proceeds"])
        self.assertEqual("$25.00", readiness["metrics"]["form_8949_cost_basis"])
        self.assertEqual("$50.00", readiness["metrics"]["form_8949_gain_loss"])

    def test_fifo_auto_link_uses_earliest_buy(self):
        transactions = empty_transactions()
        first_buy = Buy("BTC", 1, datetime.datetime(2023, 1, 1), 100, "test")
        second_buy = Buy("BTC", 1, datetime.datetime(2023, 2, 1), 200, "test")
        sell = Sell("BTC", 1, datetime.datetime(2023, 3, 1), 300, "test")
        transactions.transactions = [second_buy, sell, first_buy]

        failures = transactions.auto_link(asset="BTC", algo="fifo")

        self.assertEqual([], failures)
        self.assertEqual(first_buy.uid, sell.links[0].buy.uid)
        self.assertAlmostEqual(200, sell.links[0].profit_loss)

    def test_stats_safe_auto_fix_links_unlinked_sales_only(self):
        transactions = empty_transactions()
        buy = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "test")
        sell = Sell("BTC", 1, datetime.datetime(2024, 2, 1), 300, "test")
        mismatch_buy = Buy("SOL", 2, datetime.datetime(2024, 1, 1), 10, "test")
        transactions.transactions = [buy, sell, mismatch_buy]
        transactions.set_holdings("BTC", 0)
        transactions.set_holdings("SOL", 0)

        payload = _auto_fix_safe_issues(transactions)
        statuses = {
            row[0]: row[6]
            for row in payload["holdings_reconciliation_table_data"]
        }

        self.assertEqual(1, payload["links_created"])
        self.assertEqual(["BTC"], payload["fixed_assets"])
        self.assertEqual("Verified", statuses["BTC"])
        self.assertEqual("Needs Review", statuses["SOL"])
        self.assertIn("SOL", payload["review_required_assets"])
        self.assertIn("Added 1 FIFO basis link", payload["message"])
        self.assertEqual(
            ["Added FIFO basis links from Stats review"],
            transactions.saved_descriptions,
        )

    def test_model_sell_defaults_to_fifo(self):
        transactions = empty_transactions()
        old_buy = Buy("BTC", 1, datetime.datetime(2020, 1, 1), 100, "old")
        new_buy = Buy("BTC", 1, datetime.datetime(2021, 1, 1), 250, "new")
        transactions.transactions = [new_buy, old_buy]

        payload = _model_sale_payload(
            transactions,
            "BTC",
            sale_usd_spot=300,
            total_in_usd=300,
        )
        fifo = payload["batches_by_key"]["fifo"]

        self.assertEqual("fifo", payload["default_batch_key"])
        self.assertEqual("old", fifo["rows"][0][0])
        self.assertEqual("$100.00", fifo["summary"]["cost_basis_display"])
        self.assertEqual("$200.00", fifo["summary"]["gain_loss_display"])

    def test_model_sell_uses_declared_current_holdings_lots(self):
        transactions = empty_transactions()
        old_buy = Buy("BTC", 1, datetime.datetime(2020, 1, 1), 100, "old")
        new_buy = Buy("BTC", 1, datetime.datetime(2021, 1, 1), 250, "new")
        transactions.transactions = [old_buy, new_buy]
        transactions.set_holdings("BTC", 0.5)

        payload = _model_sale_payload(
            transactions,
            "BTC",
            sale_usd_spot=300,
            quantity=0.5,
        )
        fifo = payload["batches_by_key"]["fifo"]

        self.assertEqual("new", fifo["rows"][0][0])
        self.assertEqual("0.5", fifo["summary"]["quantity_display"])
        self.assertEqual("$125.00", fifo["summary"]["cost_basis_display"])
        self.assertEqual("$25.00", fifo["summary"]["gain_loss_display"])

    def test_min_gain_auto_link_uses_highest_cost_basis(self):
        transactions = empty_transactions()
        low_basis_buy = Buy("ETH", 1, datetime.datetime(2023, 1, 1), 100, "test")
        high_basis_buy = Buy("ETH", 1, datetime.datetime(2023, 2, 1), 250, "test")
        sell = Sell("ETH", 1, datetime.datetime(2023, 3, 1), 300, "test")
        transactions.transactions = [low_basis_buy, sell, high_basis_buy]

        failures = transactions.auto_link(asset="ETH", algo="min_gain")

        self.assertEqual([], failures)
        self.assertEqual(high_basis_buy.uid, sell.links[0].buy.uid)
        self.assertAlmostEqual(50, sell.links[0].profit_loss)

    def test_convert_sends_to_sells_creates_sell_and_conversion_record(self):
        transactions = empty_transactions()
        send = Send("SOL", 3, datetime.datetime(2024, 1, 1), 50, "wallet")
        transactions.transactions = [send]

        message = transactions.convert_sends_to_sells("SOL", amount_to_convert=2)

        sells = [trans for trans in transactions if trans.trans_type == "sell"]
        sends = [trans for trans in transactions if trans.trans_type == "send"]
        self.assertIn("Reclassified 2.0 SOL", message)
        self.assertEqual(1, len(sells))
        self.assertEqual(1, len(sends))
        self.assertAlmostEqual(2, sells[0].quantity)
        self.assertAlmostEqual(1, sends[0].quantity)
        self.assertEqual(1, len(transactions.conversions))

    def test_convert_receives_to_buys_creates_buy_and_reduces_receive(self):
        transactions = empty_transactions()
        receive = Receive("ADA", 10, datetime.datetime(2024, 1, 1), "wallet", 0.50)
        transactions.transactions = [receive]

        transactions.convert_receives_to_buys("ADA", amount_to_convert=4)

        buys = [trans for trans in transactions if trans.trans_type == "buy"]
        receives = [trans for trans in transactions if trans.trans_type == "receive"]
        self.assertEqual(1, len(buys))
        self.assertEqual(1, len(receives))
        self.assertAlmostEqual(4, buys[0].quantity)
        self.assertAlmostEqual(6, receives[0].quantity)
        self.assertEqual(1, len(transactions.conversions))

    def test_convert_buys_to_lost_uses_only_unlinked_quantity(self):
        transactions = empty_transactions()
        buy = Buy("MATIC", 5, datetime.datetime(2024, 1, 1), 1, "test")
        sell = Sell("MATIC", 2, datetime.datetime(2024, 2, 1), 2, "test")
        sell.link_transaction(buy, 2)
        transactions.transactions = [buy, sell]

        transactions.convert_buys_to_lost("MATIC", amount=2)

        self.assertAlmostEqual(3, buy.quantity)
        self.assertAlmostEqual(1, buy.unlinked_quantity)
        self.assertEqual(1, len(transactions.conversions))


if __name__ == "__main__":
    unittest.main()
