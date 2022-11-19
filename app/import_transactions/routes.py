from . import blueprint
from flask import Flask, render_template, session, redirect, url_for, session, request, current_app
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from wtforms import (SelectField,StringField,
                     SubmitField, DecimalField, DateField)

from wtforms.fields.html5 import DateField
from transaction import Buy, Sell
import json
from werkzeug.utils import secure_filename
from flask import jsonify
from conversion import Conversion

from wtforms.fields.html5 import DateTimeLocalField
from utils import *

import dateutil.parser

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


class CurrentHodl(FlaskForm):
    symbol = StringField('Crypto Symbol')
    quantity = DecimalField('Quantity', rounding=None)
    
    submit = SubmitField('Submit')


@blueprint.route('/', methods=['GET', 'POST'])
@login_required
def import_wizard():

    transactions = current_app.config['transactions']
    manual_trans = ManualTransaction()
    current_hodl = CurrentHodl()

    if 'current_hodl' not in session:
        session['current_hodl'] = []

    # if file is uploaded add new transactions 
    if request.method == 'POST':

        # Import from CSV File
        if 'file' in request.files:
            file = request.files['file']
            transactions.import_transactions(file, filename=secure_filename(file.filename))
    

        # Current Hodl
        if current_hodl.validate_on_submit():
           pass

    
    stats_table_data = get_stats_table_data(transactions)
    all_trans_table_data = get_all_trans_table_data(transactions)
    
    return render_template('import_transactions.html', manual_trans=manual_trans, current_hodl=current_hodl,transactions=all_trans_table_data, stats_table_data=stats_table_data)


