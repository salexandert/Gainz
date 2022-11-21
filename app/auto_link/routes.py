
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



@blueprint.route('/', methods=['GET'])
@login_required
def auto_link():
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)

    return render_template('auto_link.html', stats_table_data=stats_table_data)


@blueprint.route('/auto_link_asset', methods=['POST'])
@login_required
def auto_link_asset():
    transactions = current_app.config['transactions']
        
    # print(request.json)
    
    if 'asset' in request.json:
        asset = request.json['asset'][0]
    else:
        asset = None

    algo_type = request.json['algo']

    transactions.auto_link(asset=asset, algo=algo_type)

    if algo_type == "fifo":
        transactions.auto_link(asset=asset, algo=algo_type)
        transactions.save(description="Auto Linked with FIFO")

    elif algo_type == "filo":
        transactions.auto_link(asset=asset, algo=algo_type)
        transactions.save(description="Auto Linked with FILO")


    return jsonify(f"Auto Link using {algo_type} Successful!")


@blueprint.route('/auto_link_pre_check', methods=['POST'])
@login_required
def auto_link_pre_check():
    
    # print(request.json)
    
    asset = request.json['row_data'][0]

    transactions = current_app.config['transactions']

    auto_link_failures = transactions.auto_link(asset=asset, algo='fifo', pre_check=True)
    
    auto_link_failures.extend(transactions.auto_link(asset=asset, algo='filo', pre_check=True))

    auto_link_check_failed = False

    if len(auto_link_failures) > 0:
        for i in auto_link_failures:
            if i['unlinkable'] > 0.000009:
                auto_link_check_failed = True

    buys = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "buy"]
    sends = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "send"]
    receives = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "receive"]
    sells = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "sell"]

    buys.sort(key=lambda x: x.time_stamp)
    sends.sort(key=lambda x: x.time_stamp)
    receives.sort(key=lambda x: x.time_stamp)
    sells.sort(key=lambda x: x.time_stamp)
    
    sold = 0.0
    bought = 0.0
    
    for trans in transactions:
        if trans.symbol != asset:
            continue

        if trans.trans_type == "sell":
            sold += trans.quantity
        
        elif trans.trans_type == "buy":
            bought += trans.quantity


    sold_to_date = 0.0
    latest_sell_time_stamp = None
    is_greater = False
    
    auto_suggestions = {}
    auto_suggestions['pre-check'] = []

    for sell in sells:
        if is_greater is True:
            break

        latest_sell_time_stamp = sell.time_stamp
        sold_to_date += sell.quantity
        bought_to_date = 0.0
        
        for buy in buys:
            
            # check if buy came before sell and if bought_to_date < sold_to_date
            if buy.time_stamp > sell.time_stamp and (sold_to_date - bought_to_date) > 0.000000009:
                
                is_greater = True
                break

            else:
                bought_to_date += buy.quantity

    
    message = ""
    if bought >= sold:
        id = "4.2.1"
        description = "Auto-Link Pre-Check: More Buys than Sells"
        status = "Passed"
        auto_suggestions['pre-check'].append([id, description, status])
        message += description
        
        if is_greater is True:
            id = "4.2.2"
            description = (f"<br> Auto-Link Pre-Check: Individual sells can be covered by an earlier buy: At sell timestamp [{latest_sell_time_stamp}] Buy Quantity [{bought_to_date}] can no longer cover Sell Quantity [{sold_to_date}] "
             f"<br> You can track down the discrepency and add [{sold_to_date - bought_to_date}] in buys manually or by converting receives to buys before [{latest_sell_time_stamp}]."
             "<br> If you continue you will have sells not fully linked (unlinked quantity) to buys. Full proceeds on quantity unlinked of sell will be used for Gain/Loss.")
            status = "Failed"
            auto_suggestions['pre-check'].append([id, description, status])
            message += description
       
        else:

            id = "4.2.2"
            description = "<br> Auto-Link Pre-Check: Individual sells can be covered by an earlier buy"
            status = "Passed"
            auto_suggestions['pre-check'].append([id, description, status])
            message += description

            if auto_link_check_failed is True:
                id = "4.2.3"
                description = "Auto-Link Pre-Check: Sell's will be fully linked using Auto Link"
                status = "Failed"
                for i in auto_link_failures:
                    message += f"<br> {i}"
            
            else:
                id = "4.2.3"
                description = "Auto-Link Pre-Check: Sell's will be fully linked using Auto Link"
                status = "Passed"
            
            auto_suggestions['pre-check'].append([id, description, status])

    
    else:
        id = f"4.2.1"
        description = "Auto-Link Pre-Check: More Buys than Sells"
        status = "Failed"
        message += description
        auto_suggestions['pre-check'].append([id, description, status])

 
    # auto_suggestions['received_fully_linked'] = []
    # receives_fully_linked = True
    # for receive in receives:
    #     receive_index = receives.index(receive)
    #     if receive.unlinked_quantity > 0.00000001:
    #         receives_fully_linked = False
            # id = f"R:{receive_index}"

            # description = f" Received {receive.quantity} on {receive.time_stamp} this has remaining {receive.unlinked_quantity} quantity unlinked to a buy, where did it come from? \nLink to a buy to clarify"
                    
            # status = "Not Complete"
            # auto_suggestions['received_fully_linked'].append([
            #     id,
            #     description,
            #     status
            # ])
    
    # if receives_fully_linked is True:
    #     id = f"RFL:{1}"
    #     description = f"Receives are fully linked to buys."
    #     status = "Passed"
    # else:
    #     id = f"RFL:{1}"
    #     description = f"Receives are fully linked to buys. Where did it come from?"
    #     status = "Failed"
    
    # auto_suggestions['received_fully_linked'].append([
    #             id,
    #             description,
    #             status
    #         ])      

    auto_suggestions['sent_received'] = []
    for send in sends:
        send_index = sends.index(send)
                        
        for receive in receives:
            receive_index = receives.index(receive)
            
            if receive.time_stamp > send.time_stamp:
                if (receive.time_stamp - send.time_stamp).days <= 7:
                    if send.quantity >= receive.quantity:
                        difference = send.quantity - receive.quantity

                        if send.quantity * send.usd_spot < 10:
                            continue

                        if receive.quantity * receive.usd_spot < 10:
                            continue

                        
                        description = (
                            f"Sent {send.quantity} on {send.time_stamp} and received {receive.quantity} {(receive.time_stamp - send.time_stamp).days} days later"
                            f" with a difference of {difference:.9f}. If the difference is a sell create it on the Add and Manage Transactions page."
                        )

                        id = f"DIF:{send_index}:{receive_index}"
                        status = "Not Complete"

                        auto_suggestions['sent_received'].append([
                            id,
                            description,
                            status   
                        ])
    
    # post_check = []
    # auto_suggestions['post_check'] = post_check

    # unlinked_total = 0
    # for sell in sells:
    #     unlinked_total += sell.unlinked_quantity

    # if unlinked_total > .000001:
    #     post_check.append([f"PC:1", f"Auto-Link Post-Check: Sells are Fully Linked to Buys", "Failed"])
    # else:
    #     post_check.append([f"PC:1", f"Auto-Link Post-Check: Sells are Fully Linked to Buys", "Passed"])


    # all sells linked to buys. Buys unlinked Quantity = HODL

    data = {}
    data['message'] = message
    data['auto_suggestions'] =  auto_suggestions['pre-check']
    
    hodl = "N/A"
        
    for a in transactions.asset_objects:
        if a.symbol != asset:
            continue
        
        # print(f"Asset Object symbol {a.symbol} Asset {asset} HODL {a.hodl}")
        if a.hodl is not None:

            hodl = a.hodl
    
    if hodl == "N/A":
        data['auto_suggestions'].append([f"4.1.1", f"HODL Provided {hodl}", "Not Complete"])
    else:
        data['auto_suggestions'].append([f"4.1.1", f"HODL Provided {hodl}", "Complete"])

        expected_hodl = bought - sold
        hodl_difference = expected_hodl - hodl

        if hodl_difference > 0 or hodl_difference < 0:
            data['auto_suggestions'].append([f"4.1.2", f"Buys ({bought}) - sold ({sold}) = expected HODL ({expected_hodl }). expected HODL - Sells ({sold}) = difference ({hodl_difference})", "Failed"])
        else:
            data['auto_suggestions'].append([f"4.1.2", f"Buys ({bought}) - sold ({sold}) = expected HODL ({expected_hodl }). expected HODL - Sells ({sold}) = difference ({hodl_difference})", "passed"])


    return jsonify(data)






