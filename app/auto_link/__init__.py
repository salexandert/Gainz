from flask import Blueprint

blueprint = Blueprint(
    'auto_link_blueprint',
    __name__,
    url_prefix='/auto_link',
    template_folder='templates',
    static_folder='static'
)


