from flask import Blueprint

blueprint = Blueprint(
    'hodl_accounting_blueprint',
    __name__,
    url_prefix='/hodl_accounting',
    template_folder='templates',
    static_folder='static'
)


