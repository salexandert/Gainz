from flask import Blueprint

blueprint = Blueprint(
    'privacy_blueprint',
    __name__,
    url_prefix='/privacy',
    template_folder='templates',
    static_folder='static',
)
