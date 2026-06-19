import csv
import datetime
import json
import os
import subprocess
import sys
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


def _open_folder(path):
    path = Path(path).expanduser().resolve()
    if path.is_file():
        path = path.parent
    path.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])


def _open_path(path):
    path = Path(path).expanduser().resolve()
    if not path.exists():
        return False

    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])
    return True


def _work_order_rows(transactions):
    readiness = get_audit_readiness_summary(transactions)
    return [
        row for row in reconciliation_work_order_rows(readiness, transactions)
        if row.get("blocker_type") != "No open blockers"
    ]


def _work_order_why_it_matters(row):
    blocker_type = row.get("blocker_type")
    return {
        "Missing acquisition basis": (
            "Gainz cannot fully support gain/loss for this disposal until earlier acquisition "
            "records are found, documented, or intentionally left for professional review."
        ),
        "Reviewed import warning blocker": (
            "A decision was recorded, but the condition still affects generated reports or audit packet readiness."
        ),
        "Import warning decision": (
            "Skipped rows or imported rows with missing values can change holdings, proceeds, basis, or evidence review."
        ),
        "Current holdings missing": (
            "Declared holdings let Gainz compare imported activity against what the user actually holds today."
        ),
        "Holdings explanation needed": (
            "A holdings gap usually means missing transfers, disposals, losses, source files, or classification decisions."
        ),
        "Tax evidence review": (
            "Generated totals are easier to review when filed-return evidence, payment evidence, or user confirmations are recorded by year."
        ),
        "Possible overlapping source files": (
            "Overlapping source files can duplicate activity and make holdings or basis look wrong."
        ),
    }.get(blocker_type, "This item should be documented before treating the packet as complete.")


def _work_order_related_url(row):
    blocker_type = row.get("blocker_type")
    if blocker_type in {"Current holdings missing", "Holdings explanation needed", "Missing acquisition basis"}:
        return url_for("holdings_accounting_blueprint.holdings_accounting")
    if blocker_type in {"Import warning decision", "Reviewed import warning blocker", "Possible overlapping source files"}:
        return url_for("import_transactions_blueprint.import_wizard")
    if blocker_type == "Tax evidence review":
        return url_for("tax_filing_review_blueprint.index")
    return url_for("export_blueprint.index")


def _review_queue_context(transactions, item_id=""):
    rows = _work_order_rows(transactions)
    unreviewed = [row for row in rows if not row.get("review_decision")]
    current = None

    if item_id:
        current = next((row for row in rows if row.get("item_id") == item_id), None)

    if current is None:
        current = unreviewed[0] if unreviewed else None

    index = rows.index(current) + 1 if current in rows else 0
    next_item = None
    if current and unreviewed:
        current_position = rows.index(current)
        later_unreviewed = [
            row for row in rows[current_position + 1 :]
            if not row.get("review_decision") and row.get("item_id") != current.get("item_id")
        ]
        next_item = later_unreviewed[0] if later_unreviewed else next(
            (row for row in unreviewed if row.get("item_id") != current.get("item_id")),
            None,
        )
    if current:
        current["why_it_matters"] = _work_order_why_it_matters(current)
        current["related_url"] = _work_order_related_url(current)

    return {
        "rows": rows,
        "item": current,
        "index": index,
        "total": len(rows),
        "unreviewed_count": len(unreviewed),
        "reviewed_count": len(rows) - len(unreviewed),
        "next_item_id": next_item.get("item_id") if next_item else "",
        "choices": work_order_review_choices(),
    }


def _packet_manifest_counts(packet_path):
    counts = {
        "copied_files": 0,
        "reference_only_tax_evidence": 0,
        "missing_tax_evidence": 0,
    }
    manifest_path = packet_path / "03_manifests" / "evidence_manifest.csv"
    if not manifest_path.exists():
        return counts

    with open(manifest_path, newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row.get("status") == "COPIED":
                counts["copied_files"] += 1
            if row.get("category") == "tax_evidence" and row.get("status") == "REFERENCE_ONLY":
                counts["reference_only_tax_evidence"] += 1
            if row.get("category") == "tax_evidence" and row.get("status") == "MISSING":
                counts["missing_tax_evidence"] += 1
    return counts


def _folder_size(path):
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _format_bytes(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _packet_success_context(packet_path_value):
    packet_path = Path(packet_path_value or "").expanduser()
    if not packet_path.is_absolute():
        packet_path = Path.cwd() / packet_path
    packet_path = packet_path.resolve()

    summary = {}
    summary_path = packet_path / "03_manifests" / "audit_packet_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    counts = _packet_manifest_counts(packet_path)
    is_ready = bool(summary.get("readiness_is_ready"))
    blocker_groups = summary.get("readiness_blocker_groups") or []
    packet_size = _folder_size(packet_path)
    generated_at = ""
    if packet_path.exists():
        generated_at = datetime.datetime.fromtimestamp(packet_path.stat().st_mtime).strftime("%Y-%m-%d %I:%M %p")
    review_first = [
        "README_FIRST.md for the human packet orientation.",
        "PACKET_STATUS.md for readiness, blockers, warnings, and evidence counts.",
        "FOR_CPAS.md for the CPA-facing review order.",
        "03_manifests/evidence_manifest.csv for copied, reference-only, and missing evidence.",
        "01_reports/reconciliation_work_order.csv for unresolved review items.",
    ]

    return {
        "packet_path": str(packet_path),
        "packet_name": packet_path.name,
        "readme_first_path": str(packet_path / "README_FIRST.md"),
        "packet_exists": packet_path.exists() and packet_path.is_dir(),
        "status": "Filing-ready review packet" if is_ready else "Draft packet",
        "status_class": "status-verified" if is_ready else "status-needs-review",
        "is_draft": not is_ready,
        "summary": summary.get("readiness_summary", "Open the packet status file for details."),
        "generated_at": generated_at or "Unknown",
        "packet_size": _format_bytes(packet_size),
        "copied_files_count": counts["copied_files"],
        "reference_only_files_count": counts["reference_only_tax_evidence"],
        "missing_evidence_count": counts["missing_tax_evidence"],
        "open_blocker_groups": blocker_groups,
        "review_first": review_first,
        "cpa_summary": (
            f"Gainz audit packet: {'filing-ready review packet' if is_ready else 'draft packet'}. "
            f"Packet path: {packet_path}. "
            f"Summary: {summary.get('readiness_summary', 'Open PACKET_STATUS.md for details.')}. "
            f"Copied files: {counts['copied_files']}. "
            f"Reference-only tax evidence records: {counts['reference_only_tax_evidence']}. "
            f"Missing evidence paths: {counts['missing_tax_evidence']}. "
            "Recommended first files: README_FIRST.md, PACKET_STATUS.md, FOR_CPAS.md, "
            "03_manifests/evidence_manifest.csv, and 01_reports/reconciliation_work_order.csv."
        ),
    }


@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)
    audit_readiness = get_audit_readiness_summary(transactions)
    default_output_folder = _path_for_display(_default_packet_output_folder())
    work_order_rows = _work_order_rows(transactions)

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


@blueprint.route('/review_queue', methods=['GET'])
@login_required
def review_queue():
    transactions = current_app.config['transactions']
    context = _review_queue_context(transactions, item_id=request.args.get("item_id", ""))
    return render_template("review_queue.html", **context)


@blueprint.route('/review_queue/save', methods=['POST'])
@login_required
def review_queue_save():
    transactions = current_app.config['transactions']
    item_id = str(request.form.get("item_id") or "").strip()
    decision = str(request.form.get("decision") or "").strip()
    note = str(request.form.get("note") or "").strip()

    if not item_id or decision not in WORK_ORDER_REVIEW_DECISIONS:
        return redirect(url_for('export_blueprint.review_queue', item_id=item_id, saved=0))

    transactions.set_work_order_review(item_id, decision=decision, note=note)
    transactions.save(description=f"Updated review queue item: {WORK_ORDER_REVIEW_DECISIONS[decision]}")

    return redirect(url_for('export_blueprint.review_queue', saved=1))


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
        "success_url": url_for("export_blueprint.packet_success", packet_path=packet_path),
    })


@blueprint.route('/packet_success', methods=['GET'])
@login_required
def packet_success():
    packet_path = request.args.get("packet_path", "")
    if not packet_path:
        return redirect(url_for("export_blueprint.index"))

    return render_template(
        "packet_success.html",
        packet=_packet_success_context(packet_path),
    )


@blueprint.route('/open_folder', methods=['POST'])
@login_required
def open_folder():
    folder = request.form.get("folder") or request.form.get("path") or ""
    if folder:
        _open_folder(folder)
    return redirect(request.referrer or url_for("export_blueprint.index"))


@blueprint.route('/open_path', methods=['POST'])
@login_required
def open_path():
    path = request.form.get("path") or ""
    if path:
        _open_path(path)
    return redirect(request.referrer or url_for("export_blueprint.index"))

