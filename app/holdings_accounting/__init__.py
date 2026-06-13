from flask import Blueprint

blueprint = Blueprint(
    'holdings_accounting_blueprint',
    __name__,
    url_prefix='/holdings_accounting',
    template_folder='templates',
    static_folder='static'
)


