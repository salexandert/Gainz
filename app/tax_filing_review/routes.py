from flask import current_app, redirect, render_template, request, url_for
from flask_login import login_required

from utils import get_tax_filing_alignment_summary, parse_float_value


from . import blueprint


def _available_years(alignment):
    years = {row["year"] for row in alignment["rows"]}
    return sorted(years, reverse=True)


@blueprint.route('/', methods=['GET'])
@login_required
def index():
    transactions = current_app.config['transactions']
    alignment = get_tax_filing_alignment_summary(transactions)

    return render_template(
        'tax_filing_review.html',
        alignment=alignment,
        available_years=_available_years(alignment),
        saved_year=request.args.get("saved_year"),
    )


@blueprint.route('/save', methods=['POST'])
@login_required
def save_tax_year_record():
    transactions = current_app.config['transactions']
    year = int(request.form.get("year"))

    transactions.set_tax_year_record(
        year=year,
        reported_proceeds=parse_float_value(request.form.get("reported_proceeds")),
        reported_cost_basis=parse_float_value(request.form.get("reported_cost_basis")),
        reported_gain_loss=parse_float_value(request.form.get("reported_gain_loss")),
        tax_paid=parse_float_value(request.form.get("tax_paid")),
        filing_status=request.form.get("filing_status") or "Filed",
        evidence_reference=request.form.get("evidence_reference") or "",
        notes=request.form.get("notes") or "",
    )
    transactions.save(description=f"Recorded filed tax totals for {year}")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_year=year))
