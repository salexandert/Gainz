import datetime
import unittest

from app import create_app
from app.home.routes import _home_progress
from configs.config import config_dict
from transaction import Buy, Sell
from transactions import Transactions


def empty_transactions():
    transactions = Transactions.__new__(Transactions)
    transactions.transactions = []
    transactions.asset_objects = []
    transactions.import_warnings = []
    return transactions


def progress_for(transactions):
    app = create_app(config_dict["Debug"], selenium=True)
    with app.test_request_context("/home/"):
        return _home_progress(transactions)


def step_named(progress, title):
    return next(step for step in progress["steps"] if step["title"] == title)


class HomeProgressTests(unittest.TestCase):
    def test_home_progress_starts_at_import_without_transactions(self):
        progress = progress_for(empty_transactions())

        self.assertEqual("current", step_named(progress, "Import")["state"])
        self.assertEqual("waiting", step_named(progress, "Declare Holdings")["state"])
        self.assertEqual("waiting", step_named(progress, "Reconcile")["state"])
        self.assertEqual("waiting", step_named(progress, "Review & Export")["state"])

    def test_home_progress_moves_to_holdings_after_clean_import(self):
        transactions = empty_transactions()
        transactions.transactions.append(
            Buy(
                symbol="BTC",
                quantity=1,
                time_stamp=datetime.datetime(2024, 1, 1),
                usd_spot=100,
                source="test.csv",
            )
        )

        progress = progress_for(transactions)

        self.assertEqual("complete", step_named(progress, "Import")["state"])
        self.assertEqual("current", step_named(progress, "Declare Holdings")["state"])
        self.assertIn("need declared holdings", step_named(progress, "Declare Holdings")["detail"])

    def test_home_progress_highlights_reconciliation_when_sells_are_unlinked(self):
        transactions = empty_transactions()
        transactions.transactions.extend([
            Buy(
                symbol="BTC",
                quantity=1,
                time_stamp=datetime.datetime(2024, 1, 1),
                usd_spot=100,
                source="test.csv",
            ),
            Sell(
                symbol="BTC",
                quantity=0.5,
                time_stamp=datetime.datetime(2024, 2, 1),
                usd_spot=120,
                source="test.csv",
            ),
        ])
        transactions.set_holdings("BTC", 0.5)

        progress = progress_for(transactions)

        self.assertEqual("complete", step_named(progress, "Declare Holdings")["state"])
        self.assertEqual("review", step_named(progress, "Reconcile")["state"])
        self.assertEqual("waiting", step_named(progress, "Review & Export")["state"])

    def test_home_progress_marks_export_ready_after_reconciliation(self):
        transactions = empty_transactions()
        transactions.transactions.append(
            Buy(
                symbol="BTC",
                quantity=1,
                time_stamp=datetime.datetime(2024, 1, 1),
                usd_spot=100,
                source="test.csv",
            )
        )
        transactions.set_holdings("BTC", 1)

        progress = progress_for(transactions)

        self.assertEqual("complete", step_named(progress, "Import")["state"])
        self.assertEqual("complete", step_named(progress, "Declare Holdings")["state"])
        self.assertEqual("complete", step_named(progress, "Reconcile")["state"])
        self.assertEqual("ready", step_named(progress, "Review & Export")["state"])


if __name__ == "__main__":
    unittest.main()
