
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


@blueprint.route('/', methods=['POST', 'GET'])
@login_required
def hodl_accounting():
    transactions = current_app.config['transactions']
    
    stats_table_data = get_stats_table_data(transactions)

    if request.method == "POST":
        # print(request.json)

        asset = request.json['asset'][0]
        hodl = float(request.json['quantity'])

        transactions.convert_sends_to_sells(asset=asset, current_hodl=hodl)

        transactions.save(description="Converted Sends to Sells")

        return jsonify("Converted Sends to Sells!")

    
    return render_template('hodl_accounting.html', stats_table_data=stats_table_data)



@blueprint.route('/auto_suggestions',  methods=['POST'])
@login_required
def auto_suggestions():

    transactions = current_app.config['transactions']

    table_data = request.json["table_data"]
    asset = request.json['asset'][0]

    sends = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "send"]
    receives = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "receive"]
    sends.sort(key=lambda x: x.time_stamp)
    receives.sort(key=lambda x: x.time_stamp)

    # print(f"len of sends, in auto actions {len(sends)}")
    # print(f"len of receives, in auto actions {len(receives)}")

    data = []

    for row_data in table_data.values():
        if type(row_data) != list:
            continue

        if type(row_data[0]) != str:
            continue

        # Get selected Trans Object
        id = row_data[0]
        description = row_data[1]
        difference = row_data[2]

        send_index = int(id.split(':')[0])
        receive_index = int(id.split(':')[1])

        send = sends[send_index]
        receive = receives[receive_index]

        print(send.usd_spot)
        print(receive.usd_spot)

        send_usd_spot = send.usd_spot
        receive_usd_spot = receive.usd_spot

        
        data.append({
            'send_usd_spot': send_usd_spot,
            'receive_usd_spot': receive_usd_spot,
            'quantity': difference
        })


    return jsonify(data)


@blueprint.route('/hodl_info', methods=['POST'])
@login_required
def hodl_info():
    asset_symbol = request.json['asset'][0]
    hodl = float(request.json['quantity'])

    transactions = current_app.config['transactions']

    for a in transactions.asset_objects:
        # print(a.symbol, asset_symbol)
        if a.symbol != asset_symbol:
            continue 

        a.hodl = hodl
        # print(f"Setting HODL for {a.symbol} is {a.hodl}")

    for a in transactions.asset_objects:
        # print(f"Asset Object symbol {a.symbol} Asset {asset_symbol} HODL {a.hodl}")
        if a.hodl is not None:
            hodl = a.hodl
            # print(f"Asset Object symbol {a.symbol} Asset {asset_symbol} HODL {a.hodl}")

    transactions.save(description=f"Added HODL for {asset_symbol}")

    return jsonify("HODL Accepted")



@blueprint.route('/sends_to_sells', methods=['POST'])
@login_required
def sends_to_sells():
    
    transactions = current_app.config['transactions']
    asset = request.json['asset'][0]
    amount_to_convert = float(request.json['quantity'])

    quantity_of_sends_converted_to_sells = None
    number_of_converted_transactions = None

    for a in transactions.asset_objects:
        if a.symbol != asset:
            continue 
        
        result_str = transactions.convert_sends_to_sells(asset=asset, amount_to_convert=amount_to_convert)

        transactions.save(description="Converted Sends to sells")

    auto_link_failures = transactions.auto_link(asset=asset, algo='fifo', pre_check=True)

    if len(auto_link_failures) > 0:
        for failure in auto_link_failures:
            
            send_to_delete = None

            for trans in transactions:
                if trans.trans_type != "sell":
                    continue

                if trans.symbol != failure['asset']:
                    continue
                    
                if trans.quantity != failure['quantity']:
                    continue
            
                if trans.time_stamp != failure['timestamp']:
                    continue

                send_to_delete = trans
                break
            
            if send_to_delete is not None:
                print(f"We need to delete \n [{send_to_delete}] \n")
                # quantity = send_to_delete.quantity
                # del(send_to_delete)

    return jsonify(result_str)



@blueprint.route('/buys_to_lost', methods=['POST'])
@login_required
def buys_to_lost():
   
    transactions = current_app.config['transactions']

    # print(request.json)

    asset = request.json['asset'][0]
    amount = float(request.json['quantity'])

    transactions.convert_buys_to_lost(asset=asset, amount=amount)

    transactions.save(description="Converted Buys to Lost")

    return jsonify("Yess")
    

@blueprint.route('/receive_to_buy', methods=['POST'])
@login_required
def receive_to_buy():
    
    transactions = current_app.config['transactions']
    
    asset = request.json['asset'][0]
    amount_to_convert = float(request.json['quantity'])
    
    for a in transactions.asset_objects:
        if a.symbol != asset:
            continue 
        
        transactions.convert_receives_to_buys(asset=asset, amount_to_convert=amount_to_convert)

        transactions.save(description="Converted receives to buys")

        # current_app.config['transactions'] = transactions.load()

    return jsonify("Yess")