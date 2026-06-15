import datetime
import unittest

from app import create_app
from app.home.routes import _home_progress
from configs.config import config_dict
from transaction import Buy, Sell
from transactions import Transactions
from utils import get_audit_readiness_summary


def empty_transactions():
    transactions = Transactions.__new__(Transactions)
    transactions.transactions = []
    transactions.asset_objects = []
    transactions.import_warnings = []
    transactions.import_warning_reviews = []
    transactions.basis_review_notes = []
    transactions.tax_year_records = []
    transactions.tax_evidence_records = []
    transactions.saves = []
    transactions.conversions = []
    return transactions


def progress_for(transactions):
    app = create_app(config_dict["Debug"], selenium=True)
    with app.test_request_context("/home/"):
        return _home_progress(transactions)


def render_home_page(transactions):
    app = create_app(config_dict["Debug"], selenium=True)
    with app.test_request_context("/home/"):
        return app.jinja_env.get_template("home.html").render(
            home_progress=_home_progress(transactions),
            audit_readiness=get_audit_readiness_summary(transactions),
            store_url=None,
            support_url=None,
            btc_receive_address=None,
        )


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

    def test_home_page_keeps_simple_cards_and_only_marks_completed_steps(self):
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

        rendered = render_home_page(transactions)

        self.assertIn("Load exchange CSVs or demo data.", rendered)
        self.assertIn("Review missing activity before using reports.", rendered)
        self.assertIn("Reconciliation Dashboard", rendered)
        self.assertIn("Open Review Groups", rendered)
        self.assertNotIn("gainz-home-flow-heading", rendered)
        self.assertNotIn("gainz-home-flow-detail", rendered)
        self.assertNotIn("Start by importing source files.", rendered)
        self.assertNotIn("is-ready", rendered)
        self.assertEqual(3, rendered.count("gainz-home-flow-step is-complete"))


if __name__ == "__main__":
    unittest.main()
