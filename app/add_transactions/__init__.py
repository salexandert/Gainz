from flask import Blueprint

blueprint = Blueprint(
    'add_transactions_blueprint',
    __name__,
    url_prefix='/add_transactions',
    template_folder='templates',
    static_folder='static'
)


