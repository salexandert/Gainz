from flask_migrate import Migrate
from configs.config import config_dict
from app import create_app, db
from transactions import Transactions
import sys, os


get_config_mode = os.environ.get('GENTELELLA_CONFIG_MODE', 'Debug')

try:
    config_mode = config_dict[get_config_mode.capitalize()]
except KeyError:
    sys.exit('Error: Invalid GENTELELLA_CONFIG_MODE environment variable entry.')


transactions = Transactions()
app = create_app(config_mode)
app.config['transactions'] = transactions
Migrate(app, db)


# import logging
# logging.basicConfig(filename='gainz.log', level=logging.DEBUG)
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)


if __name__ == "__main__":

    print(f"\n\nGainz App runs on a non-production (Flask) web server you can safely ignore the warning(s) below. \n\nTo access Gainz to go http://127.0.0.1:5000 in a web browser. Preferably Chrome\n")
    print(f"Default credentials username: admin, password: admin\n")
    print("Close this window when finished.\n")
    
    app.run(debug=True)
 
