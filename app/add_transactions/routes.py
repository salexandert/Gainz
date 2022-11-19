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


@blueprint.route('/', methods=['GET', 'POST'])
@login_required
def add_transaction():

    transactions = current_app.config['transactions']
    manual_trans = ManualTransaction()

    stats_table_data = get_stats_table_data(transactions)


    # Import Manual trans
    if manual_trans.is_submitted():
        

        # print(manual_trans.data)
        if manual_trans.type.data == 'buy':
            trans = Buy(
                trans_type=manual_trans.type.data,
                time_stamp=manual_trans.timestamp.data, 
                quantity=float(manual_trans.quantity.data), 
                usd_spot=float(manual_trans.usd_spot.data), 
                symbol=manual_trans.symbol.data.upper(),
                source="Gainz App Manual Add"
                )
        
        elif manual_trans.type.data == 'sell':
            trans = Sell(
                trans_type=manual_trans.type.data, 
                time_stamp=manual_trans.timestamp.data, 
                quantity=float(manual_trans.quantity.data), 
                usd_spot=float(manual_trans.usd_spot.data),
                symbol=manual_trans.symbol.data.upper(),
                source="Gainz App Manual Add"
                )
        
        
        transactions.transactions.append(trans)

        transactions.save(description="Manually Added Transaction")
        
        trans_data = {}
        trans_data['name'] = trans.name
        trans_data['type'] = trans.trans_type
        trans_data['asset'] = trans.symbol
        trans_data['time_stamp'] = trans.time_stamp
        trans_data['usd_spot'] = "${:,.2f}".format(trans.usd_spot)
        trans_data['quantity'] = trans.quantity
        trans_data['unlinked_quantity'] = trans.unlinked_quantity
        trans_data['usd_total'] = "${:,.2f}".format(trans.usd_total)
    
        stats_table_data = get_stats_table_data(transactions)
        
    return render_template('add_transactions.html',  manual_trans=manual_trans, stats_table_data=stats_table_data)


@blueprint.route('/add_transactions_selected_asset',  methods=['POST'])
@login_required
def add_transactions_selected_asset():

    # print(request.json)

    transactions = current_app.config['transactions']

    date_range = {
        'start_date': '',
        'end_date': ''
    }

    asset = request.json['row_data'][0]

    # Get date range of transactions
    date_range = get_transactions_date_range(transactions, date_range)

     # Get Sells Table Data 
    sells_table_data = get_sells_trans_table_data_range(transactions, asset, date_range)

    # Get Buys Table Data
    buys_table_data = get_buys_trans_table_data_range(transactions, asset, date_range)

    buys_unlinked_remaining = []
    if request.json['unlinked_remaining']:
        for buy in buys_table_data:
            if type(buy[4]) is str:
                continue

            if buy[4] > 0.000000009:
                buys_unlinked_remaining.append(buy)

        buys_table_data = buys_unlinked_remaining

    
    if 'usd_spot' in request.json:
        print(request.json['usd_spot'])
        usd_spot = float(request.json['usd_spot'].replace(',', ''))
        for row in buys_table_data:
            if row[4] == 'Less than 0.00000009' or row[4] == '0':
                remaining_in_usd = row[4]
            else:
                remaining_in_usd = usd_spot * float(row[4])
                remaining_in_usd = "${:,.2f}".format(remaining_in_usd)
            
            row.append(remaining_in_usd)
    else:
        for row in buys_table_data:
            row.append("Provide USD Spot to Populate")

    # Get Sends Table Data
    sends_table_data = get_sends_trans_table_data_range(transactions, asset, date_range)

    # Get Receives Table Data
    receives_table_data = get_receives_trans_table_data_range(transactions, asset, date_range)


    data_dict = {}
    data_dict['sells'] = sells_table_data
    data_dict['buys'] = buys_table_data
    data_dict['sends'] = sends_table_data
    data_dict['receives'] = receives_table_data


    return jsonify(data_dict)


@blueprint.route('/delete_transactions',  methods=['POST'])
@login_required
def delete_transactions():

    asset = request.json['asset'][0]
    trans_type = request.json['type']

    transactions = current_app.config['transactions']

    # Get selected Trans Object
    row_data = request.json['row_data']
    symbol = row_data[1]
    time_stamp_str = row_data[2]
    time_stamp = dateutil.parser.parse(time_stamp_str)
    quantity = row_data[3]
    usd_spot = row_data[5]

    trans_obj = get_trans_obj_from_table_data(transactions=transactions, symbol=symbol, trans_type=trans_type, quantity=quantity, time_stamp=time_stamp)

    if trans_obj is not None:
        
        transactions.transactions.remove(trans_obj)

        transactions.save(f'Deleted {asset} {trans_type} {quantity}')

        return jsonify(f'Deleted {asset} {trans_type} {quantity} on {time_stamp}')
    
    else:

        return jsonify(f'Transaction Not Found! {asset} {trans_type} {quantity}')


@blueprint.route('/buy_convert',  methods=['POST'])
@login_required
def buy_convert():

    # print(request.json)

    transactions = current_app.config['transactions']

    # Get selected Trans Object
    row_data = request.json['row_data']
    symbol = row_data[1]
    time_stamp_str = row_data[2]
    time_stamp = dateutil.parser.parse(time_stamp_str)
    quantity = row_data[3]
    usd_spot = row_data[5]

    trans_obj = get_trans_obj_from_table_data(transactions=transactions, symbol=symbol, trans_type='buy', quantity=quantity, time_stamp=time_stamp)

    if trans_obj is not None:

        if len(trans_obj.links) > 0:
            return jsonify(f"{trans_obj.trans_type} has {len(trans_obj.links)} links cannot convert!")
        
        else:
            conversion = Conversion(input_trans_type='buy', 
                                    output_trans_type='lost', 
                                    input_symbol=trans_obj.symbol, 
                                    input_quantity=trans_obj.quantity, 
                                    input_time_stamp=trans_obj.time_stamp, 
                                    input_usd_spot=trans_obj.usd_spot, 
                                    input_usd_total=trans_obj.usd_total, 
                                    reason="Converted Buy to Lost", 
                                    source=f"{trans_obj.source} Converted in Gainz App")

            transactions.conversions.append(conversion)
            
            transactions.transactions.remove(trans_obj)

            transactions.save(description=f"Converted {symbol} Buy to Lost")

            return jsonify(f'Converted Buy to Lost {trans_obj.name}')


@blueprint.route('/receive_convert',  methods=['POST'])
@login_required
def receive_convert():

    transactions = current_app.config['transactions']

    table_data = request.json['table_data']

    for row_data in table_data.values():
        if type(row_data) != list:
            continue

        if type(row_data[0]) != str:
            continue

        # Get selected Trans Object
        symbol = row_data[1]
        time_stamp_str = row_data[2]
        time_stamp = dateutil.parser.parse(time_stamp_str)
        quantity = row_data[3]
        usd_spot = row_data[5]

        receive_obj = get_trans_obj_from_table_data(transactions=transactions, symbol=symbol, trans_type='receive', quantity=quantity, time_stamp=time_stamp)

        if receive_obj is not None:

            buy = Buy(symbol=symbol, quantity=receive_obj.quantity, time_stamp=receive_obj.time_stamp, usd_spot=receive_obj.usd_spot, source="Gainz App Receive to Buy")
                
            conversion = Conversion(input_trans_type='receive', 
                                    output_trans_type='buy', 
                                    input_symbol=receive_obj.symbol, 
                                    input_quantity=receive_obj.quantity, 
                                    input_time_stamp=receive_obj.time_stamp, 
                                    input_usd_spot=receive_obj.usd_spot, 
                                    input_usd_total=receive_obj.usd_total, 
                                    reason="Converted Receive to Buy", 
                                    source=f"{receive_obj.source} Converted in Gainz App")

            transactions.conversions.append(conversion)
            
            transactions.transactions.append(buy)

            transactions.transactions.remove(receive_obj)

    transactions.save(description=f"Converted receive(s) to buy(s)")

    return jsonify(f'Converted Receive(s) to Buy {receive_obj.name}')


@blueprint.route('/send_convert',  methods=['POST'])
@login_required
def send_convert():

    # print(request.json)

    transactions = current_app.config['transactions']

    # Get selected Trans Object
    row_data = request.json['row_data']
    symbol = row_data[1]
    time_stamp_str = row_data[2]
    time_stamp = dateutil.parser.parse(time_stamp_str)
    quantity = row_data[3]
    usd_spot = row_data[5]

    send_obj = get_trans_obj_from_table_data(transactions=transactions, symbol=symbol, trans_type='send', quantity=quantity, time_stamp=time_stamp)

    if send_obj is not None:

            sell = Sell(symbol=symbol, quantity=send_obj.quantity, time_stamp=send_obj.time_stamp, usd_spot=send_obj.usd_spot, source="Gainz App Send to Sell")
                
            conversion = Conversion(input_trans_type='send', 
                                    output_trans_type='sell', 
                                    input_symbol=send_obj.symbol, 
                                    input_quantity=send_obj.quantity, 
                                    input_time_stamp=send_obj.time_stamp, 
                                    input_usd_spot=send_obj.usd_spot, 
                                    input_usd_total=send_obj.usd_total, 
                                    reason="Converted Send to Sell", 
                                    source=f"{send_obj.source} Converted in Gainz App")

            transactions.conversions.append(conversion)
            
            transactions.transactions.append(sell)

            transactions.transactions.remove(send_obj)

            transactions.save(description=f"Converted {symbol} Send to Sell")

            return jsonify(f'Converted Receive to Buy {send_obj.name}')


