from . import blueprint
from flask import current_app, render_template, request, url_for
from flask_login import login_required
from utils import (
    get_audit_readiness_summary,
    get_multi_asset_holdings_reconciliation_table_data,
)
from app.services.import_warning_service import unresolved_import_warning_rows


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
    import_warning_count = len(unresolved_import_warning_rows(transactions))
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
            "url": url_for("import_transactions_blueprint.import_wizard", guided=1),
            "action_label": "Open Import",
            "state": "current",
            "status": "Current",
            "detail": "Start by importing source files.",
        },
        {
            "number": 2,
            "title": "Declare Holdings",
            "description": "Enter what you actually hold today.",
            "url": url_for("holdings_accounting_blueprint.holdings_accounting", guided=1, mode="declare"),
            "action_label": "Declare Holdings",
            "state": "waiting",
            "status": "Waiting",
            "detail": "Import transactions first.",
        },
        {
            "number": 3,
            "title": "Reconcile",
            "description": "Review missing activity before using reports.",
            "url": url_for("holdings_accounting_blueprint.holdings_accounting", guided=1, mode="reconcile"),
            "action_label": "Reconcile",
            "state": "waiting",
            "status": "Waiting",
            "detail": "Declare holdings before reconciling.",
        },
        {
            "number": 4,
            "title": "Review & Export",
            "description": "Review readiness, model sales, and generate outputs.",
            "url": url_for("export_blueprint.index", guided=1),
            "action_label": "Open Reports & Export",
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
            "url": url_for("import_transactions_blueprint.import_wizard", guided=1) + "#import_warning_workflow",
            "action_label": (
                f"Review {import_warning_count} import "
                f"{_plural(import_warning_count, 'warning')}"
            ),
            "detail": (
                f"{import_warning_count} import "
                f"{_plural(import_warning_count, 'warning')} "
                f"{'needs' if import_warning_count == 1 else 'need'} review."
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
            "url": url_for("holdings_accounting_blueprint.holdings_accounting", guided=1, mode="declare"),
            "action_label": "Enter holdings",
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
            "url": url_for("holdings_accounting_blueprint.holdings_accounting", guided=1, mode="reconcile"),
            "action_label": "Review reconciliation",
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
        "url": url_for("export_blueprint.index", guided=1),
        "action_label": "Review & Export",
        "detail": "Review reports and generate exports.",
    })

    return {"steps": steps}


def _coerce_stage_number(value, default_stage, step_count):
    try:
        stage_number = int(value)
    except (TypeError, ValueError):
        return default_stage

    if stage_number < 1 or stage_number > step_count:
        return default_stage
    return stage_number


def _default_stage_number(steps):
    for step in steps:
        if step["state"] in {"current", "review", "ready"}:
            return step["number"]
    return steps[-1]["number"] if steps else 1


def _stage_tasks(step_number):
    tasks = {
        1: [
            "Import exchange CSVs or demo data.",
            "Use column review when Gainz cannot confidently map the file.",
            "Add source-backed manual rows for known buys or sells.",
        ],
        2: [
            "Enter what you currently hold across exchanges, wallets, and custody accounts.",
            "Use bulk holdings tools when most assets are zero.",
            "Save holdings before relying on reconciliation status.",
        ],
        3: [
            "Review holdings differences, owner-transfer questions, and missing basis.",
            "Document research notes for unresolved assets.",
            "Run FIFO basis linking when sales have missing cost basis.",
        ],
        4: [
            "Review packet readiness and the guided review queue.",
            "Confirm tax evidence, filed totals, and draft acknowledgements.",
            "Generate the workbook or audit packet when the review status is acceptable.",
        ],
    }
    return tasks.get(step_number, [])


def _stage_examples(step_number):
    examples = {
        1: [
            "A Cash App or Coinbase CSV gives Gainz source rows to review.",
            "If a header is unusual, Advanced Import lets you choose the right columns.",
        ],
        2: [
            "If you now only hold BTC, save BTC and set the rest to zero.",
            "If an old asset is gone, zero holdings helps Gainz look for the missing explanation.",
        ],
        3: [
            "A BTC withdrawal may be your own wallet transfer or a disposal that needs evidence.",
            "A sale has missing cost basis when Gainz cannot find enough earlier buy or receive lots.",
            "A holdings difference may point to missing source files, duplicate imports, or transfers that need notes.",
        ],
        4: [
            "A draft packet can document unresolved research items for CPA review.",
            "Reference-only evidence lists file paths without copying private tax files into the packet.",
        ],
    }
    return examples.get(step_number, [])


def _stage_done_criteria(step_number):
    criteria = {
        1: [
            "At least one exchange CSV, demo file, or source-backed manual row is loaded.",
            "Import warnings and possible overlapping source files are reviewed or noted.",
            "Known missing rows are added manually or left for later research with source notes.",
        ],
        2: [
            "Current holdings are saved for every imported asset.",
            "Assets you no longer hold are intentionally confirmed as zero.",
            "You have a current balance source you can review later if needed.",
        ],
        3: [
            "Holdings differences, transfer questions, and missing-basis items have decisions or notes.",
            "FIFO or another basis-linking review has been run when sales have missing cost basis.",
            "Anything still unresolved is marked for research, draft, or CPA review.",
        ],
        4: [
            "Readiness and packet preview are reviewed before generating files.",
            "Draft acknowledgement is used when unresolved blockers remain.",
            "The generated workbook or packet is opened and checked against source records.",
        ],
    }
    return criteria.get(step_number, [])


def _stage_status_class(step, current_step, audit_readiness):
    if step["number"] == current_step["number"]:
        return audit_readiness["status_class"]
    if step["state"] == "complete":
        return "status-verified"
    if step["state"] == "review":
        return "status-needs-review"
    if step["state"] == "ready":
        return "status-verified"
    return "status-needs-user-research"


def _stage_context(progress, audit_readiness, selected_stage_number=None):
    steps = progress["steps"]
    default_stage = _default_stage_number(steps)
    selected_number = _coerce_stage_number(selected_stage_number, default_stage, len(steps))
    selected_step = next(step for step in steps if step["number"] == selected_number)
    current_step = next(step for step in steps if step["number"] == default_stage)
    is_future_step = (
        selected_step["number"] > current_step["number"]
        and selected_step["state"] == "waiting"
    )
    rail_active_number = current_step["number"] if is_future_step else selected_step["number"]
    preview_step_number = selected_step["number"] if is_future_step else None

    if is_future_step:
        primary_action = {
            "label": f"Go to Step {current_step['number']}",
            "url": url_for("home_blueprint.index", stage=current_step["number"]),
            "detail": current_step["detail"],
        }
    else:
        action_url = selected_step["url"]
        primary_action = {
            "label": selected_step.get("action_label")
            if selected_step["number"] == current_step["number"]
            else f"Open {selected_step['title']}",
            "url": action_url,
            "detail": selected_step["detail"],
        }

    previous_stage = None
    next_stage = None
    next_stage_locked = False
    if not is_future_step:
        if selected_number > 1:
            previous_stage = selected_number - 1
        if selected_number < len(steps):
            next_step = next(step for step in steps if step["number"] == selected_number + 1)
            if next_step["state"] == "waiting" and selected_number >= current_step["number"]:
                next_stage_locked = True
            else:
                next_stage = next_step["number"]

    return {
        "selected_step": selected_step,
        "current_step": current_step,
        "is_future_step": is_future_step,
        "rail_active_number": rail_active_number,
        "preview_step_number": preview_step_number,
        "selected_status_class": _stage_status_class(
            selected_step,
            current_step,
            audit_readiness,
        ),
        "primary_action": primary_action,
        "tasks": _stage_tasks(selected_step["number"]),
        "examples": _stage_examples(selected_step["number"]),
        "done_criteria": _stage_done_criteria(selected_step["number"]),
        "previous_stage": previous_stage,
        "next_stage": next_stage,
        "next_stage_locked": next_stage_locked,
        "step_count": len(steps),
    }

@blueprint.route('/',  methods=['GET'])
@login_required
def index():
    transactions = current_app.config['transactions']
    home_progress = _home_progress(transactions)
    audit_readiness = get_audit_readiness_summary(transactions)

    return render_template(
        'home.html',
        home_progress=home_progress,
        audit_readiness=audit_readiness,
        stage_context=_stage_context(
            home_progress,
            audit_readiness,
            request.args.get("stage"),
        ),
    )
