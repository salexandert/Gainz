from flask import Flask, url_for
from flask_login import current_user
from .extensions import db, login_manager
from importlib import import_module
from .base.models import User
from os import path
import logging
from transactions import Transactions
import os
import secrets


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
        'hodl_accounting', 
        'home', 
        'import_transactions',
        'model',
        'setting',
        'stats',
  
        ):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):

    @app.before_request
    def initialize_database():
        if not hasattr(app, 'db_initialized'):
            db.create_all()
            admin_username = app.config['ADMIN']['username']
            user = User.query.filter_by(username=admin_username).first()
            if user is None:
                admin_config = dict(app.config['ADMIN'])
                if not admin_config.get('password'):
                    admin_config['password'] = secrets.token_urlsafe(18)
                    os.makedirs(app.config['INSTANCE_PATH'], exist_ok=True)
                    credentials_path = os.path.join(
                        app.config['INSTANCE_PATH'],
                        'first_run_credentials.txt'
                    )
                    with open(credentials_path, 'w', encoding='utf-8') as credentials_file:
                        credentials_file.write(
                            'Gainz first-run local credentials\n'
                            f"Username: {admin_config['username']}\n"
                            f"Password: {admin_config['password']}\n"
                            '\nChange this password after logging in.\n'
                        )
                    app.logger.warning(
                        'Generated first-run admin credentials at %s',
                        credentials_path
                    )
                User(**admin_config).add_to_db()
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
        Is_admin = current_user.is_authenticated and current_user.username == app.config['ADMIN']['username']
        return dict(url_for = _generate_url_for_theme,
                    Is_admin = Is_admin,
                    store_url = app.config.get('STORE_URL'),
                    support_url = app.config.get('SUPPORT_URL'))

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
    
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    configure_logs(app)
    apply_themes(app)


    return app
