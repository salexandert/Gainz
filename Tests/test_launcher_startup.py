import unittest
import tempfile
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from app import create_app
from app.base.models import User
from app.extensions import db
from configs.config import config_dict
from launcher import find_available_port, health_url, server_url
from password_reset import DOCUMENTED_RESET_PHRASE, reset_admin_password
from port_guard import require_port_available
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
        self.assertIn("/holdings_accounting", rendered_nav)
        self.assertNotIn("Search...", rendered_nav)
        self.assertNotIn("nc-layout-11", rendered_nav)

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
        self.assertIn("Step 4: Review Readiness", rendered_page)
        self.assertIn('id="holdings_readiness_badge"', rendered_page)
        self.assertIn('id="holdings_run_fifo_button"', rendered_page)
        self.assertIn("Technical pre-check details", rendered_page)

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

    def test_port_guard_refuses_occupied_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            occupied_port = sock.getsockname()[1]

            with self.assertRaises(RuntimeError):
                require_port_available("127.0.0.1", occupied_port)

    def test_launcher_refuses_configured_occupied_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            occupied_port = sock.getsockname()[1]

            with patch.dict("os.environ", {"GAINZ_PORT": str(occupied_port)}):
                with self.assertRaises(RuntimeError):
                    find_available_port()

    def test_first_run_setup_creates_local_admin_without_plaintext_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class FirstRunTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                ADMIN = {
                    "username": "admin",
                    "email": "admin@local.gainz",
                    "password": "",
                }

            app = create_app(FirstRunTestConfig, selenium=True)

            with app.test_client() as client:
                response = client.get("/login")
                self.assertEqual(200, response.status_code)
                self.assertIn(b"Create Local Admin", response.data)

                response = client.post(
                    "/login",
                    data={
                        "username": "admin",
                        "email": "admin@local.gainz",
                        "password": "local-password",
                        "create_account": "1",
                    },
                )
                self.assertEqual(302, response.status_code)

            self.assertFalse((Path(temp_dir) / "first_run_credentials.txt").exists())

            with app.app_context():
                self.assertEqual(1, User.query.count())
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_protected_page_redirects_to_login_instead_of_403(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class AuthRedirectTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                ADMIN = {
                    "username": "admin",
                    "email": "admin@local.gainz",
                    "password": "",
                }

            app = create_app(AuthRedirectTestConfig)

            with app.test_client() as client:
                response = client.get("/stats/")

            self.assertEqual(302, response.status_code)
            location = urlparse(response.headers["Location"])
            self.assertEqual("/login", location.path)
            self.assertEqual(["/stats/"], parse_qs(location.query)["next"])

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_login_returns_to_safe_next_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class AuthRedirectTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                ADMIN = {
                    "username": "admin",
                    "email": "admin@local.gainz",
                    "password": "local-password",
                }

            app = create_app(AuthRedirectTestConfig)

            with app.test_client() as client:
                response = client.post(
                    "/login?next=/stats/",
                    data={
                        "username": "admin",
                        "password": "local-password",
                        "login": "1",
                    },
                )

            self.assertEqual(302, response.status_code)
            self.assertEqual("/stats/", urlparse(response.headers["Location"]).path)

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_login_ignores_external_next_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class AuthRedirectTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                ADMIN = {
                    "username": "admin",
                    "email": "admin@local.gainz",
                    "password": "local-password",
                }

            app = create_app(AuthRedirectTestConfig)

            with app.test_client() as client:
                response = client.post(
                    "/login?next=https://example.com/phishing",
                    data={
                        "username": "admin",
                        "password": "local-password",
                        "login": "1",
                    },
                )

            self.assertEqual(302, response.status_code)
            self.assertEqual("/home/", urlparse(response.headers["Location"]).path)

            with app.app_context():
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_password_reset_updates_existing_local_admin(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class PasswordResetTestConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                ADMIN = {
                    "username": "admin",
                    "email": "admin@local.gainz",
                    "password": "",
                }

            app = create_app(PasswordResetTestConfig, selenium=True)

            with app.app_context():
                db.create_all()
                User(username="admin", email="admin@local.gainz", password="old-password").add_to_db()
                db.session.remove()
                db.engine.dispose()

            result = reset_admin_password(
                password=DOCUMENTED_RESET_PHRASE,
                config_class=PasswordResetTestConfig,
            )

            self.assertFalse(result.created)
            self.assertEqual("admin", result.username)

            verify_app = create_app(PasswordResetTestConfig, selenium=True)
            with verify_app.app_context():
                user = User.query.filter_by(username="admin").first()
                self.assertIsNotNone(user)
                self.assertTrue(user.checkpw(DOCUMENTED_RESET_PHRASE))
                self.assertFalse(user.checkpw("old-password"))
                db.drop_all()
                db.session.remove()
                db.engine.dispose()

    def test_password_reset_creates_missing_local_admin(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            class PasswordResetCreateConfig(config_dict["Debug"]):
                TESTING = True
                WTF_CSRF_ENABLED = False
                INSTANCE_PATH = temp_dir
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{temp_dir}/test.db"
                ADMIN = {
                    "username": "admin",
                    "email": "admin@local.gainz",
                    "password": "",
                }

            result = reset_admin_password(
                password=DOCUMENTED_RESET_PHRASE,
                config_class=PasswordResetCreateConfig,
            )

            self.assertTrue(result.created)
            self.assertEqual("admin", result.username)

            verify_app = create_app(PasswordResetCreateConfig, selenium=True)
            with verify_app.app_context():
                user = User.query.filter_by(username="admin").first()
                self.assertIsNotNone(user)
                self.assertTrue(user.checkpw(DOCUMENTED_RESET_PHRASE))
                db.drop_all()
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
