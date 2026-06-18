from pathlib import Path

from . import blueprint
from flask import render_template, request, jsonify, current_app, redirect, url_for
from flask_login import login_required
from utils import *
from app.services.export_service import ExportService
from app.services.audit_packet_service import AuditPacketService
from app.services.packet_plan_service import (
    WORK_ORDER_REVIEW_DECISIONS,
    get_packet_preview,
    reconciliation_work_order_rows,
    work_order_review_choices,
)


def _path_for_display(path):
    return str(Path(path).expanduser().resolve())


def _detected_tax_folder():
    candidate = Path.home() / "OneDrive" / "Taxes"
    return str(candidate) if candidate.exists() and candidate.is_dir() else ""


def _default_packet_output_folder():
    return _detected_tax_folder() or current_app.config['AUDIT_PACKET_FOLDER']


def _requested_output_dir(default_folder):
    payload = request.get_json(silent=True) or {}
    requested = str(payload.get("output_dir") or "").strip()
    output_dir = Path(requested).expanduser() if requested else Path(default_folder)

    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError("Output location must be a folder, not a file.")

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.resolve()


def _preview_output_dir(default_folder):
    payload = request.get_json(silent=True) or {}
    requested = str(
        payload.get("output_dir")
        or request.args.get("output_dir")
        or request.form.get("output_dir")
        or ""
    ).strip()
    output_dir = Path(requested).expanduser() if requested else Path(default_folder)

    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError("Output location must be a folder, not a file.")

    return output_dir.resolve()


def _truthy_payload_value(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _draft_acknowledged():
    payload = request.get_json(silent=True) or {}
    return _truthy_payload_value(payload.get("draft_acknowledged") or request.form.get("draft_acknowledged"))


def _draft_ack_error(transactions, output_label):
    readiness = get_audit_readiness_summary(transactions)
    if readiness["is_ready"] or _draft_acknowledged():
        return None

    return jsonify({
        "message": (
            f"{output_label} is draft-only because Gainz still has unresolved review items. "
            "Check the draft acknowledgement before generating files."
        ),
        "status": readiness["status"],
        "requires_draft_acknowledgement": True,
    }), 400


def _draft_workbook_path(path):
    path = Path(path)
    if path.name.startswith("DRAFT_"):
        return str(path)

    candidate = path.with_name(f"DRAFT_{path.name}")
    if not candidate.exists():
        path.replace(candidate)
        return str(candidate)

    index = 2
    while True:
        candidate = path.with_name(f"DRAFT_{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            path.replace(candidate)
            return str(candidate)
        index += 1


@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)
    audit_readiness = get_audit_readiness_summary(transactions)
    default_output_folder = _path_for_display(_default_packet_output_folder())
    work_order_rows = [
        row for row in reconciliation_work_order_rows(audit_readiness, transactions)
        if row.get("blocker_type") != "No open blockers"
    ]

    return render_template(
        'export.html',
        stats_table_data=stats_table_data,
        audit_readiness=audit_readiness,
        export_folder=_path_for_display(current_app.config['EXPORT_FOLDER']),
        audit_packet_folder=_path_for_display(current_app.config['AUDIT_PACKET_FOLDER']),
        detected_tax_folder=_detected_tax_folder(),
        packet_preview=get_packet_preview(transactions, audit_readiness, default_output_folder),
        work_order_rows=work_order_rows,
        work_order_review_choices=work_order_review_choices(),
    )


@blueprint.route('/work_order_review', methods=['POST'])
@login_required
def work_order_review():
    transactions = current_app.config['transactions']
    payload = request.get_json(silent=True) or {}
    item_id = str(payload.get("item_id") or request.form.get("item_id") or "").strip()
    decision = str(payload.get("decision") or request.form.get("decision") or "").strip()
    note = str(payload.get("note") or request.form.get("note") or "").strip()

    if not item_id:
        if request.is_json:
            return jsonify({"message": "Work order item id is required."}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    if decision not in WORK_ORDER_REVIEW_DECISIONS:
        if request.is_json:
            return jsonify({"message": "Choose a valid work order review state."}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    transactions.set_work_order_review(item_id, decision=decision, note=note)
    transactions.save(description=f"Updated work order item: {WORK_ORDER_REVIEW_DECISIONS[decision]}")

    if request.is_json:
        return jsonify({
            "item_id": item_id,
            "decision": decision,
            "decision_label": WORK_ORDER_REVIEW_DECISIONS[decision],
        })

    return redirect(url_for('export_blueprint.index', work_order_reviewed=1))


@blueprint.route('/packet_preview.json', methods=['GET', 'POST'])
@login_required
def packet_preview_json():
    transactions = current_app.config['transactions']
    try:
        output_dir = _preview_output_dir(_default_packet_output_folder())
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    readiness = get_audit_readiness_summary(transactions)
    return jsonify({
        "packet_preview": get_packet_preview(transactions, readiness, output_dir),
        "readiness": {
            "status": readiness["status"],
            "status_class": readiness["status_class"],
            "is_ready": readiness["is_ready"],
            "summary": readiness["summary"],
            "next_action": readiness["next_action"],
            "blocker_groups": readiness["blocker_groups"],
            "metrics": readiness["metrics"],
        },
    })


@blueprint.route('/save',  methods=['POST'])
@login_required
def save():
    transactions = current_app.config['transactions']
    draft_error = _draft_ack_error(transactions, "Workbook export")
    if draft_error:
        return draft_error

    try:
        output_dir = _requested_output_dir(current_app.config['EXPORT_FOLDER'])
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    readiness = get_audit_readiness_summary(transactions)
    save_as_filename = ExportService(str(output_dir)).export_to_excel(
        transactions,
        readiness=readiness,
    )
    if not readiness["is_ready"]:
        save_as_filename = _draft_workbook_path(save_as_filename)

    print(f"exporting to {save_as_filename}")

    return jsonify({
        "path": save_as_filename,
        "output_dir": str(output_dir),
    })


@blueprint.route('/audit_packet',  methods=['POST'])
@login_required
def audit_packet():
    transactions = current_app.config['transactions']
    draft_error = _draft_ack_error(transactions, "Audit packet")
    if draft_error:
        return draft_error

    try:
        output_dir = _requested_output_dir(current_app.config['AUDIT_PACKET_FOLDER'])
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    packet_path = AuditPacketService(
        str(output_dir),
        str(output_dir),
    ).create_packet(transactions)

    return jsonify({
        "path": packet_path,
        "output_dir": str(output_dir),
    })
    

