import os
import secrets


def _local_instance_path():
    return os.environ.get(
        'GAINZ_INSTANCE_PATH',
        os.path.join(os.getcwd(), 'instance')
    )


def _read_or_create_secret_key():
    env_secret = os.environ.get('GAINZ_SECRET_KEY')
    if env_secret:
        return env_secret

    instance_path = _local_instance_path()
    os.makedirs(instance_path, exist_ok=True)
    secret_path = os.path.join(instance_path, 'secret_key')

    if os.path.exists(secret_path):
        with open(secret_path, 'r', encoding='utf-8') as secret_file:
            return secret_file.read().strip()

    secret = secrets.token_urlsafe(48)
    with open(secret_path, 'w', encoding='utf-8') as secret_file:
        secret_file.write(secret)

    return secret


def _admin_config():
    return {
        'username': os.environ.get('GAINZ_ADMIN_USERNAME', 'admin'),
        'email': os.environ.get('GAINZ_ADMIN_EMAIL', 'admin@local.gainz'),
        'password': os.environ.get('GAINZ_ADMIN_PASSWORD', ''),
    }

class Config(object):
    SECRET_KEY = _read_or_create_secret_key()
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STORE_URL = os.environ.get('GAINZ_STORE_URL', 'https://cryptogainz.store')
    SUPPORT_URL = os.environ.get(
        'GAINZ_SUPPORT_URL',
        'https://cash.app/$SAl3xander'
    )
    BTC_RECEIVE_ADDRESS = os.environ.get(
        'GAINZ_BTC_RECEIVE_ADDRESS',
        'bc1q5ptf8aylwauthxr80x60k554c3xdv2lpe046t4'
    )
    INSTANCE_PATH = _local_instance_path()
    UPLOAD_FOLDER = os.environ.get(
        'GAINZ_UPLOAD_FOLDER',
        os.path.join(os.getcwd(), 'uploads')
    )
    EXPORT_FOLDER = os.environ.get(
        'GAINZ_EXPORT_FOLDER',
        os.path.join(os.getcwd(), 'exports')
    )
    AUDIT_PACKET_FOLDER = os.environ.get(
        'GAINZ_AUDIT_PACKET_FOLDER',
        os.path.join(os.getcwd(), 'audit_packets')
    )
    ADMIN = _admin_config()

    # THEME SUPPORT
    #  if set then url_for('static', filename='', theme='')
    #  will add the theme name to the static URL:
    #    /static/<DEFAULT_THEME>/filename
    # DEFAULT_THEME = "themes/dark"
    DEFAULT_THEME = None


class ProductionConfig(Config):
    DEBUG = False

    # PostgreSQL database
    SQLALCHEMY_DATABASE_URI = 'postgresql://{}:{}@{}:{}/{}'.format(
        os.environ.get('GENTELELLA_DATABASE_USER', 'gentelella'),
        os.environ.get('GENTELELLA_DATABASE_PASSWORD', 'gentelella'),
        os.environ.get('GENTELELLA_DATABASE_HOST', 'db'),
        os.environ.get('GENTELELLA_DATABASE_PORT', 5432),
        os.environ.get('GENTELELLA_DATABASE_NAME', 'gentelella')
    )


class DebugConfig(Config):
    DEBUG = True


config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}
