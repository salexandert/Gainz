from flask import Blueprint

blueprint = Blueprint(
    'add_transactions_blueprint',
    __name__,
    url_prefix='/import_data',
    template_folder='templates',
    static_folder='static'
)


