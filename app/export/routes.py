from pathlib import Path

from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from utils import *
from app.services.export_service import ExportService
from app.services.audit_packet_service import AuditPacketService


def _path_for_display(path):
    return str(Path(path).expanduser().resolve())


def _detected_tax_folder():
    candidate = Path.home() / "OneDrive" / "Taxes"
    return str(candidate) if candidate.exists() and candidate.is_dir() else ""


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


@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)
    audit_readiness = get_audit_readiness_summary(transactions)

    return render_template(
        'export.html',
        stats_table_data=stats_table_data,
        audit_readiness=audit_readiness,
        export_folder=_path_for_display(current_app.config['EXPORT_FOLDER']),
        audit_packet_folder=_path_for_display(current_app.config['AUDIT_PACKET_FOLDER']),
        detected_tax_folder=_detected_tax_folder(),
    )


@blueprint.route('/save',  methods=['POST'])
@login_required
def save():
    transactions = current_app.config['transactions']

    try:
        output_dir = _requested_output_dir(current_app.config['EXPORT_FOLDER'])
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    save_as_filename = ExportService(str(output_dir)).export_to_excel(transactions)

    print(f"exporting to {save_as_filename}")

    return jsonify({
        "path": save_as_filename,
        "output_dir": str(output_dir),
    })


@blueprint.route('/audit_packet',  methods=['POST'])
@login_required
def audit_packet():
    transactions = current_app.config['transactions']

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
    

