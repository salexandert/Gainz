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
                return jsonify(result)

        # Current holdings
        if current_holdings.validate_on_submit():
            pass

    stats_table_data = get_stats_table_data(transactions)
    all_trans_table_data = get_all_trans_table_data(transactions)

    return render_template('import_transactions.html', manual_trans=manual_trans, current_holdings=current_holdings, transactions=all_trans_table_data, stats_table_data=stats_table_data)


