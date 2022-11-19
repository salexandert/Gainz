from flask import Blueprint

blueprint = Blueprint(
    'model_blueprint',
    __name__,
    url_prefix='/model',
    template_folder='templates',
    static_folder='static'
)
