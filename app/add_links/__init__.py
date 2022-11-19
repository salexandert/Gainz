from flask import Blueprint

blueprint = Blueprint(
    'add_links_blueprint',
    __name__,
    url_prefix='/add_links',
    template_folder='templates',
    static_folder='static'
)


