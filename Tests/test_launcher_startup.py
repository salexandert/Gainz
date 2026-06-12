import unittest

from app import create_app
from configs.config import config_dict
from launcher import health_url, server_url


class LauncherStartupTests(unittest.TestCase):
    def test_health_route_is_registered_for_launcher_readiness(self):
        app = create_app(config_dict["Debug"], selenium=True)
        rules = {rule.rule for rule in app.url_map.iter_rules()}

        self.assertIn("/healthz", rules)

    def test_account_password_route_is_available_from_top_nav(self):
        app = create_app(config_dict["Debug"], selenium=True)

        with app.test_request_context("/"):
            rendered_nav = app.jinja_env.get_template(
                "site_template/top_navigation.html"
            ).render()

        self.assertIn("/setting/change_password", rendered_nav)
        self.assertIn("Change password", rendered_nav)

    def test_launcher_health_url_uses_local_server_url(self):
        self.assertEqual("http://127.0.0.1:5000", server_url(5000))
        self.assertEqual("http://127.0.0.1:5000/healthz", health_url(5000))


if __name__ == "__main__":
    unittest.main()
