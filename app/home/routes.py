from . import blueprint
from flask import current_app, render_template, url_for
from flask_login import login_required
from utils import (
    get_audit_readiness_summary,
    get_multi_asset_holdings_reconciliation_table_data,
)


def _plural(count, singular, plural=None):
    return singular if count == 1 else (plural or f"{singular}s")


def _unlinked_sale_assets(transactions):
    assets = set()

    for transaction in getattr(transactions, "transactions", []) or []:
        if getattr(transaction, "trans_type", "") != "sell":
            continue

        if getattr(transaction, "unlinked_quantity", 0) > 0.000000009:
            assets.add(getattr(transaction, "symbol", ""))

    return sorted(asset for asset in assets if asset)


def _home_progress(transactions):
    transaction_count = len(getattr(transactions, "transactions", []) or [])
    asset_count = len(getattr(transactions, "assets", set()) or set())
    import_warning_count = len(getattr(transactions, "import_warnings", []) or [])
    holdings_rows = (
        get_multi_asset_holdings_reconciliation_table_data(transactions)
        if transaction_count
        else []
    )
    assets_needing_holdings = [
        row[0]
        for row in holdings_rows
        if len(row) > 6 and row[6] == "Needs declared holdings"
    ]
    assets_with_mismatches = [
        row[0]
        for row in holdings_rows
        if len(row) > 6 and row[6] == "Needs Review"
    ]
    unlinked_sale_assets = _unlinked_sale_assets(transactions)
    has_reconciliation_issues = bool(assets_with_mismatches or unlinked_sale_assets)

    steps = [
        {
            "number": 1,
            "title": "Import",
            "description": "Load exchange CSVs or demo data.",
            "url": url_for("import_transactions_blueprint.import_wizard"),
            "state": "current",
            "status": "Current",
            "detail": "Start by importing source files.",
        },
        {
            "number": 2,
            "title": "Declare Holdings",
            "description": "Enter what you actually hold today.",
            "url": url_for("holdings_accounting_blueprint.holdings_accounting"),
            "state": "waiting",
            "status": "Waiting",
            "detail": "Import transactions first.",
        },
        {
            "number": 3,
            "title": "Reconcile",
            "description": "Review missing activity before using reports.",
            "url": url_for("holdings_accounting_blueprint.holdings_accounting"),
            "state": "waiting",
            "status": "Waiting",
            "detail": "Declare holdings before reconciling.",
        },
        {
            "number": 4,
            "title": "Review & Export",
            "description": "Review readiness, model sales, and generate outputs.",
            "url": url_for("export_blueprint.index"),
            "state": "waiting",
            "status": "Waiting",
            "detail": "Resolve earlier stages first.",
        },
    ]

    if transaction_count == 0:
        return {"steps": steps}

    if import_warning_count:
        steps[0].update({
            "state": "review",
            "status": "Needs Review",
            "detail": (
                f"{import_warning_count} import "
                f"{_plural(import_warning_count, 'warning')} need review."
            ),
        })
        steps[1]["detail"] = "Resolve import warnings before relying on holdings."
        return {"steps": steps}

    steps[0].update({
        "state": "complete",
        "status": "Complete",
        "detail": (
            f"{transaction_count} "
            f"{_plural(transaction_count, 'transaction')} across "
            f"{asset_count} {_plural(asset_count, 'asset')} loaded."
        ),
    })

    if assets_needing_holdings:
        count = len(assets_needing_holdings)
        steps[1].update({
            "state": "current",
            "status": "Current",
            "detail": (
                f"{count} {_plural(count, 'asset')} still "
                "need declared holdings."
            ),
        })
        return {"steps": steps}

    steps[1].update({
        "state": "complete",
        "status": "Complete",
        "detail": "Declared holdings are saved for imported assets.",
    })

    if has_reconciliation_issues:
        review_count = len(set(assets_with_mismatches + unlinked_sale_assets))
        steps[2].update({
            "state": "review",
            "status": "Needs Review",
            "detail": (
                f"{review_count} {_plural(review_count, 'asset')} "
                "need reconciliation review."
            ),
        })
        steps[3]["detail"] = "Review reconciliation before export."
        return {"steps": steps}

    steps[2].update({
        "state": "complete",
        "status": "Complete",
        "detail": "No holdings discrepancies or unlinked sales detected.",
    })
    steps[3].update({
        "state": "ready",
        "status": "Ready",
        "detail": "Review reports and generate exports.",
    })

    return {"steps": steps}

@blueprint.route('/',  methods=['GET'])
@login_required
def index():
    transactions = current_app.config['transactions']

    return render_template(
        'home.html',
        home_progress=_home_progress(transactions),
        audit_readiness=get_audit_readiness_summary(transactions),
    )
