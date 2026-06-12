from flask_migrate import Migrate
from configs.config import config_dict
from app import create_app, db
from transactions import Transactions
import sys
import os
import webbrowser

from single_instance import SingleInstanceLock


get_config_mode = os.environ.get("GENTELELLA_CONFIG_MODE", "Debug")
_single_instance_lock = None

if __name__ == "__main__":
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _single_instance_lock = SingleInstanceLock(_base_dir)
    if not _single_instance_lock.acquire():
        _info = _single_instance_lock.read_info()
        _port = int(_info.get("port") or os.environ.get("GAINZ_PORT", "5000"))
        _url = _info.get("url") or f"http://127.0.0.1:{_port}"
        print(f"Gainz is already running or starting at {_url}")
        try:
            webbrowser.open(_url)
        except Exception:
            pass
        sys.exit(0)

try:
    config_mode = config_dict[get_config_mode.capitalize()]
except KeyError:
    sys.exit("Error: Invalid GENTELELLA_CONFIG_MODE environment variable entry.")


transactions = Transactions()
app = create_app(config_mode)
app.config["transactions"] = transactions
Migrate(app, db)


import logging
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Set up logging with timestamp in filename
log_filename = f'logs/gainz_{datetime.now().strftime("%Y-%m-%d")}.log'
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce werkzeug (Flask's built-in server) logging level
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configure parsers logging
parsers_logger = logging.getLogger('parsers')
parsers_logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    host = os.environ.get("GAINZ_HOST", "127.0.0.1")
    port = int(os.environ.get("GAINZ_PORT", "5000"))
    url = f"http://{host}:{port}"
    if _single_instance_lock:
        _single_instance_lock.write_info(port=port, url=url, status="running")
    debug_enabled = os.environ.get("GAINZ_FLASK_DEBUG", "").lower() in (
        "1",
        "true",
        "yes",
    )

    print(f"Logging to: {os.path.abspath(log_filename)}")
    print(
        "\n\nGainz App runs on a non-production (Flask) web server you can safely ignore the warning(s) below."
    )
    print(
        f"\nTo access Gainz go to {url} in a web browser. Preferably Chrome"
    )
    print(
        "\nIf this is your first run, credentials are in instance/first_run_credentials.txt "
        "unless GAINZ_ADMIN_PASSWORD was provided."
    )
    print("\nClose this window when finished.\n")

    try:
        app.run(host=host, port=port, debug=debug_enabled, use_reloader=False)
    finally:
        if _single_instance_lock:
            _single_instance_lock.release()
