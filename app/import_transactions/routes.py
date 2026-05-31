from . import blueprint
from flask import Flask, render_template, session, redirect, url_for, session, request, current_app
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from wtforms import (SelectField,StringField,
                     SubmitField, DecimalField, DateField)

from wtforms.fields import DateField
from transaction import Buy, Sell
import json
from flask import jsonify
from conversion import Conversion

from wtforms.fields import DateTimeLocalField
from utils import *

import dateutil.parser
import os

from flask import Blueprint, request
from transactions import Transactions
from app.services.import_service import ImportService

import_transactions_bp = Blueprint('import_transactions', __name__)

class ManualTransaction(FlaskForm):
    '''
    Manual Transaction values
    '''
    timestamp = DateTimeLocalField('Timestamp', format='%Y-%m-%dT%H:%M')
    type  = SelectField(u'Type', choices=[('buy', 'Buy'), ('sell', 'Sell')])
    symbol = StringField('Crypto Symbol')
    quantity = DecimalField('Quantity', rounding=None)
    usd_spot = DecimalField('USD Spot', rounding=None)

    submit = SubmitField('Submit')


class CurrentHoldings(FlaskForm):
    symbol = StringField('Crypto Symbol')
    quantity = DecimalField('Quantity', rounding=None)

    submit = SubmitField('Submit')


@blueprint.route('/', methods=['GET', 'POST'])
@login_required
def import_wizard():
    transactions = current_app.config['transactions']
    manual_trans = ManualTransaction()
    current_holdings = CurrentHoldings()

    if 'current_holdings' not in session:
        session['current_holdings'] = []

    # if file is uploaded add new transactions
    if request.method == 'POST':
        # Import from CSV File
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                result = ImportService(current_app.config['UPLOAD_FOLDER']).import_upload(file, transactions)
                if result.get("mapping_required"):
                    session["pending_import_file_path"] = result["file_path"]
                return jsonify(result)

        # Current holdings
        if current_holdings.validate_on_submit():
            pass

    stats_table_data = get_stats_table_data(transactions)
    all_trans_table_data = get_all_trans_table_data(transactions)

    return render_template('import_transactions.html', manual_trans=manual_trans, current_holdings=current_holdings, transactions=all_trans_table_data, stats_table_data=stats_table_data)


@blueprint.route('/mapping_preview', methods=['POST'])
@login_required
def mapping_preview():
    file_path = session.get("pending_import_file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Upload a CSV before mapping columns."}), 400

    data = request.get_json(silent=True) or {}
    header_row = data.get("header_row") or 1
    analysis = ImportService(current_app.config['UPLOAD_FOLDER']).analyze_import_file(
        file_path,
        header_row=header_row,
    )
    return jsonify({"mapping": analysis})


@blueprint.route('/mapped_import', methods=['POST'])
@login_required
def mapped_import():
    file_path = session.get("pending_import_file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Upload a CSV before mapping columns."}), 400

    data = request.get_json(silent=True) or {}
    header_row = data.get("header_row") or 1
    column_mapping = data.get("column_mapping") or {}

    transactions = current_app.config['transactions']
    result = ImportService(current_app.config['UPLOAD_FOLDER']).import_mapped_file(
        file_path,
        transactions,
        header_row=header_row,
        column_mapping=column_mapping,
    )

    if not result.get("mapping_required"):
        session.pop("pending_import_file_path", None)

    return jsonify(result)


@blueprint.route('/demo', methods=['POST'])
@login_required
def import_demo_data():
    transactions = current_app.config['transactions']
    result = ImportService(current_app.config['UPLOAD_FOLDER']).import_demo_data(
        transactions,
        repo_root=current_app.root_path + "/..",
    )
    return jsonify(result)


