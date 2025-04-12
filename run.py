from flask_migrate import Migrate
from configs.config import config_dict
from app import create_app, db
from transactions import Transactions
import sys
import os


get_config_mode = os.environ.get("GENTELELLA_CONFIG_MODE", "Debug")

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

print(f"Logging to: {os.path.abspath(log_filename)}")


if __name__ == "__main__":

    print(
        "\n\nGainz App runs on a non-production (Flask) web server you can safely ignore the warning(s) below."
    )
    print(
        "\nTo access Gainz go to http://127.0.0.1:5000 in a web browser. Preferably Chrome"
    )
    print("\nDefault credentials username: admin, password: admin")
    print("\nClose this window when finished.\n")

    app.run(debug=True)
