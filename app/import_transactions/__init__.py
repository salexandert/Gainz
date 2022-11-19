from flask import Blueprint

blueprint = Blueprint(
    'import_transactions_blueprint',
    __name__,
    url_prefix='/import_transactions',
    template_folder='templates',
    static_folder='static'
)


