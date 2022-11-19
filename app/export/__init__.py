from flask import Blueprint

blueprint = Blueprint(
    'export_blueprint',
    __name__,
    url_prefix='/export',
    template_folder='templates',
    static_folder='static'
)
