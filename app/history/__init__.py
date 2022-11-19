from flask import Blueprint

blueprint = Blueprint(
    'history_blueprint',
    __name__,
    url_prefix='/history',
    template_folder='templates',
    static_folder='static'
)
