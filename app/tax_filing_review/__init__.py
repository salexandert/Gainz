from flask import Blueprint

blueprint = Blueprint(
    'tax_filing_review_blueprint',
    __name__,
    url_prefix='/tax_filing_review',
    template_folder='templates',
    static_folder='static',
)
