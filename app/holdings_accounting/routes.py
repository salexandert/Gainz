
from . import blueprint
from flask import Flask, render_template, session, redirect, url_for, session, request, current_app
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from wtforms import (SelectField,StringField,
                     SubmitField, DecimalField, DateField)

from wtforms.fields import DateField
from transaction import Buy, Sell
import json
from werkzeug.utils import secure_filename
from flask import jsonify
from conversion import Conversion

from wtforms.fields import DateTimeLocalField
from utils import *

import dateutil.parser


def _holdings_stats_rows(stats_table_data):
    return [
        [
            row['symbol'],
            row['total_purchased_quantity'],
            row['total_sold_quantity'],
            row['total_sold_unlinked_quantity'],
            row['total_purchased_unlinked_quantity'],
            row['total_purchased_usd'],
            row['total_sold_usd'],
            row.get('total_profit_loss', row.get('profit_loss_total')),
            row['holdings'],
        ]
        for row in stats_table_data
    ]


def _holdings_summary(transactions):
    rows = get_multi_asset_holdings_reconciliation_table_data(transactions)
    return {
        "asset_count": len(rows),
        "assets_needing_holdings": sum(1 for row in rows if row[1] == "N/A"),
        "assets_matched": sum(1 for row in rows if row[6] == "Verified"),
        "assets_with_mismatch": sum(1 for row in rows if row[6] == "Needs Review"),
    }


@blueprint.route('/', methods=['POST', 'GET'])
@login_required
def holdings_accounting():
    transactions = current_app.config['transactions']

    stats_table_data = get_stats_table_data(transactions)

    if request.method == "POST":
        # print(request.json)

        asset = request.json['asset'][0]
        holdings = float(request.json['quantity'])

        transactions.convert_sends_to_sells(asset=asset, current_holdings=holdings)

        transactions.save(description="Recorded documented sends as taxable disposals")

        return jsonify("Recorded documented sends as taxable disposals for review.")


    return render_template(
        'holdings_accounting.html',
        stats_table_data=stats_table_data,
        holdings_summary=_holdings_summary(transactions),
    )



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


@blueprint.route('/holdings_info', methods=['POST'])
@login_required
def holdings_info():
    asset_symbol = request.json['asset'][0]
    holdings = float(request.json['quantity'])

    transactions = current_app.config['transactions']
    transactions.set_holdings(asset_symbol, holdings)

    transactions.save(description=f"Added holdings for {asset_symbol}")

    stats_table_data = get_stats_table_data(transactions)

    return jsonify({
        "message": f"Declared holdings for {asset_symbol} saved.",
        "stats_table_rows": _holdings_stats_rows(stats_table_data),
        "holdings_summary": _holdings_summary(transactions),
    })


@blueprint.route('/difference_breakdown', methods=['POST'])
@login_required
def difference_breakdown():
    asset_data = request.json.get('asset') if request.json else None
    asset_symbol = asset_data[0] if isinstance(asset_data, list) else asset_data

    transactions = current_app.config['transactions']

    return jsonify(get_holdings_difference_breakdown(transactions, asset_symbol))



@blueprint.route('/sends_to_sells', methods=['POST'])
@login_required
def sends_to_sells():

    transactions = current_app.config['transactions']
    asset = request.json['asset'][0]
    amount_to_convert = float(request.json['quantity'])

    result_str = transactions.convert_sends_to_sells(asset=asset, amount_to_convert=amount_to_convert)
    transactions.save(description="Recorded documented sends as taxable disposals")

    return jsonify(result_str)



@blueprint.route('/buys_to_lost', methods=['POST'])
@login_required
def buys_to_lost():

    transactions = current_app.config['transactions']

    # print(request.json)

    asset = request.json['asset'][0]
    amount = float(request.json['quantity'])

    transactions.convert_buys_to_lost(asset=asset, amount=amount)

    transactions.save(description="Marked documented buy lots for loss review")

    return jsonify("Marked documented buy lots for loss review. Review tax treatment before relying on generated reports.")


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

        transactions.save(description="Reclassified documented receives as buys")

        # current_app.config['transactions'] = transactions.load()

    return jsonify("Reclassified documented receives as buys for review.")
