from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from utils import *
from app.services.export_service import ExportService
from app.services.audit_packet_service import AuditPacketService




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
    )


@blueprint.route('/save',  methods=['POST'])
@login_required
def save():
    
    transactions = current_app.config['transactions']

    save_as_filename = ExportService(current_app.config['EXPORT_FOLDER']).export_to_excel(transactions)

    print(f"exporting to {save_as_filename}")

    return jsonify(save_as_filename)


@blueprint.route('/audit_packet',  methods=['POST'])
@login_required
def audit_packet():
    transactions = current_app.config['transactions']

    packet_path = AuditPacketService(
        current_app.config['AUDIT_PACKET_FOLDER'],
        current_app.config['EXPORT_FOLDER'],
    ).create_packet(transactions)

    return jsonify(packet_path)
    

