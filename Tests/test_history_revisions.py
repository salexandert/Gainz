import tempfile
import unittest
from pathlib import Path

from app import create_app
from configs.config import config_dict


class FakeTransactions:
    def __init__(self, saves):
        self.saves = saves
        self.view = saves[-1]["value"]
        self.loaded = None
        self.saved_description = None

    def load_saves(self):
        return self.saves

    def load(self, filename):
        self.loaded = filename
        return []

    def save(self, description=None):
        self.saved_description = description
        return str(Path(self.view).with_name("saved_restored.xlsx"))


class HistoryRevisionTests(unittest.TestCase):
    def make_app_with_saves(self, temp_dir):
        old_save = str(Path(temp_dir) / "saved_old.xlsx")
        current_save = str(Path(temp_dir) / "saved_current.xlsx")
        transactions = FakeTransactions([
            {
                "value": old_save,
                "description": "Imported Coinbase CSV",
                "revision_num": 7,
                "modified_time": 1710000000,
            },
            {
                "value": current_save,
                "description": "Current working save",
                "revision_num": 8,
                "modified_time": 1720000000,
            },
        ])

        app = create_app(config_dict["Debug"], selenium=True)
        app.config["transactions"] = transactions
        return app, transactions, old_save

    def test_history_page_lists_revisions_and_restore_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app, transactions, old_save = self.make_app_with_saves(temp_dir)

            response = app.test_client().get("/history/")
            text = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Revision History", text)
        self.assertIn("Imported Coinbase CSV", text)
        self.assertIn("Restore as Latest", text)
        self.assertIn(old_save, text)

    def test_revert_restores_known_save_as_new_revision(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app, transactions, old_save = self.make_app_with_saves(temp_dir)

            response = app.test_client().post(
                "/history/revert",
                data={"file": old_save},
                follow_redirects=False,
            )

        self.assertEqual(302, response.status_code)
        self.assertEqual(old_save, transactions.loaded)
        self.assertIn("Restored revision 7", transactions.saved_description)

    def test_revert_rejects_unknown_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app, transactions, old_save = self.make_app_with_saves(temp_dir)

            response = app.test_client().post(
                "/history/revert",
                json={"data": [str(Path(temp_dir) / "not_a_gainz_save.xlsx")]},
            )

        self.assertEqual(400, response.status_code)
        self.assertIsNone(transactions.loaded)


if __name__ == "__main__":
    unittest.main()
