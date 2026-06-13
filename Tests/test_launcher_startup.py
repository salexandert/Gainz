import unittest
import tempfile

from app import create_app
from configs.config import config_dict
from launcher import health_url, server_url
from single_instance import SingleInstanceLock


class LauncherStartupTests(unittest.TestCase):
    def test_health_route_is_registered_for_launcher_readiness(self):
        app = create_app(config_dict["Debug"], selenium=True)
        rules = {rule.rule for rule in app.url_map.iter_rules()}

        self.assertIn("/healthz", rules)
        self.assertIn("/tax_filing_review/", rules)

    def test_account_routes_are_available_from_top_nav(self):
        app = create_app(config_dict["Debug"], selenium=True)

        with app.test_request_context("/"):
            rendered_nav = app.jinja_env.get_template(
                "site_template/top_navigation.html"
            ).render()

        self.assertIn("Account settings", rendered_nav)
        self.assertIn("/setting/change_password", rendered_nav)
        self.assertIn("Change Password", rendered_nav)
        self.assertIn("/logout", rendered_nav)
        self.assertIn("Logout", rendered_nav)

    def test_holdings_workbench_title_has_asset_update_hook(self):
        app = create_app(config_dict["Debug"], selenium=True)

        with app.test_request_context("/holdings_accounting/"):
            rendered_page = app.jinja_env.get_template(
                "holdings_accounting.html"
            ).render(
                stats_table_data=[],
                holdings_summary={
                    "asset_count": 0,
                    "assets_needing_holdings": 0,
                    "assets_matched": 0,
                    "assets_with_mismatch": 0,
                },
            )

        self.assertIn('id="holdings_workbench_title"', rendered_page)
        self.assertIn("Step 3 Asset Workbench", rendered_page)

    def test_launcher_health_url_uses_local_server_url(self):
        self.assertEqual("http://127.0.0.1:5000", server_url(5000))
        self.assertEqual("http://127.0.0.1:5000/healthz", health_url(5000))

    def test_single_instance_lock_blocks_competing_gainz_process(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = SingleInstanceLock(temp_dir)
            second = SingleInstanceLock(temp_dir)

            try:
                self.assertTrue(first.acquire())
                first.write_info(port=5007, url="http://127.0.0.1:5007", status="running")

                self.assertFalse(second.acquire())
                self.assertEqual("http://127.0.0.1:5007", second.read_info()["url"])

                first.release()
                self.assertTrue(second.acquire())
            finally:
                first.release()
                second.release()


if __name__ == "__main__":
    unittest.main()
