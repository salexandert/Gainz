from flask import Flask, redirect, request, url_for
from flask_login import current_user
from .extensions import db, login_manager
from importlib import import_module
from .base.models import User, is_local_admin, local_admin_user
from os import path
import logging
from transactions import Transactions
from app_version import APP_VERSION
from local_login import login_setup_required


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app):
    for module_name in (
        'add_links',
        'add_transactions',
        'auto_link',
        'base',
        'export',
        'history',
        'holdings_accounting',
        'home',
        'import_transactions',
        'model',
        'privacy',
        'setting',
        'stats',
        'tax_filing_review',

        ):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

    @app.route('/add_transactions', defaults={'path': ''}, methods=['GET', 'POST'])
    @app.route('/add_transactions/', defaults={'path': ''}, methods=['GET', 'POST'])
    @app.route('/add_transactions/<path:path>', methods=['GET', 'POST'])
    def legacy_add_transactions_redirect(path):
        return redirect(url_for('import_transactions_blueprint.import_wizard'), code=308)


def configure_database(app):

    @app.before_request
    def initialize_database():
        if not hasattr(app, 'db_initialized'):
            db.create_all()
            admin_username = app.config['ADMIN']['username']
            user = local_admin_user(admin_username)
            setup_required = login_setup_required(app.config['INSTANCE_PATH'])
            if user is None and app.config['ADMIN'].get('password') and not setup_required:
                admin_config = dict(app.config['ADMIN'])
                User(**admin_config).add_to_db()
            elif user is None:
                app.logger.warning(
                    'No admin account exists. Open Gainz locally and create one on the first-run setup screen.'
                )
            app.db_initialized = True

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

def configure_logs(app):
    # for combine gunicorn logging and flask built-in logging module
    if __name__ != "__main__":
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
    # endif

def apply_themes(app):
    """
    Add support for themes.

    If DEFAULT_THEME is set then all calls to
      url_for('static', filename='')
      will modfify the url to include the theme name

    The theme parameter can be set directly in url_for as well:
      ex. url_for('static', filename='', theme='')

    If the file cannot be found in the /static/<theme>/ lcation then
      the url will not be modified and the file is expected to be
      in the default /static/ location
    """
    @app.context_processor
    def override_url_for():
        Is_admin = is_local_admin(current_user, app.config['ADMIN']['username'])
        return dict(url_for = _generate_url_for_theme,
                    Is_admin = Is_admin,
                    store_url = app.config.get('STORE_URL'),
                    support_url = app.config.get('SUPPORT_URL'),
                    btc_receive_address = app.config.get('BTC_RECEIVE_ADDRESS'))

    def _generate_url_for_theme(endpoint, **values):
        if endpoint.endswith('static'):
            themename = values.get('theme', None) or \
                app.config.get('DEFAULT_THEME', None)
            if themename:
                theme_file = "{}/{}".format(themename, values.get('filename', ''))
                if path.isfile(path.join(app.static_folder, theme_file)):
                    values['filename'] = theme_file
        return url_for(endpoint, **values)


def create_app(config, selenium=False):

    app = Flask(__name__, static_folder='base/static')
    app.config.from_object(config)
    if selenium:
        app.config['LOGIN_DISABLED'] = True

    @app.route('/healthz')
    def healthz():
        return {'status': 'ok', 'version': APP_VERSION}

    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    configure_logs(app)
    apply_themes(app)


    return app
