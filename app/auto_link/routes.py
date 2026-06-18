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
from app.services.auto_link_service import AutoLinkService


def _auto_link_preview_time(trans):
    return trans.time_stamp.replace(tzinfo=None) if hasattr(trans.time_stamp, 'replace') else trans.time_stamp


def _preview_auto_link_failures(asset, buys, sells, algo, min_unlinked=0.000001):
    reverse_buys = algo == 'filo'
    ordered_buys = sorted(buys, key=_auto_link_preview_time, reverse=reverse_buys)
    ordered_sells = sorted(sells, key=_auto_link_preview_time)
    buy_remaining = {id(buy): buy.unlinked_quantity for buy in ordered_buys}
    failures = []

    for sell in ordered_sells:
        sell_remaining = sell.unlinked_quantity
        if sell_remaining <= min_unlinked:
            continue

        for buy in ordered_buys:
            if sell_remaining <= min_unlinked:
                break

            if buy_remaining[id(buy)] <= min_unlinked:
                continue

            if _auto_link_preview_time(buy) >= _auto_link_preview_time(sell):
                continue

            link_quantity = min(sell_remaining, buy_remaining[id(buy)])
            link_quantity = round_decimals_down(link_quantity)
            if link_quantity <= min_unlinked:
                continue

            profit = (sell.usd_spot - buy.usd_spot) * link_quantity
            if abs(profit) < 1.0:
                continue

            buy_remaining[id(buy)] -= link_quantity
            sell_remaining -= link_quantity

        if (sell_remaining * sell.usd_spot) > min_unlinked:
            failures.append({
                'asset': asset,
                'unlinkable': sell_remaining,
                'quantity': sell.quantity,
                'timestamp': sell.time_stamp,
                'algo': algo,
            })

    return failures



@blueprint.route('/', methods=['GET'])
@login_required
def auto_link():
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)

    # Get Years
    years = set()
    for trans in transactions:
        years.add(trans.time_stamp.year)

    years = sorted(years)
    years.insert(0, 'All Time')

    return render_template('auto_link.html', stats_table_data=stats_table_data, years=years)


@blueprint.route('/auto_link_asset', methods=['POST'])
@login_required
def auto_link_asset():
    transactions = current_app.config['transactions']
    payload = request.get_json(silent=True) or {}

    if 'asset' in payload:
        asset_value = payload['asset']
        asset = asset_value[0] if isinstance(asset_value, list) else asset_value
    else:
        asset = None

    service = AutoLinkService()
    year = service.selected_year(payload.get('year', 'All Time'))

    algo_type = payload.get('algo', 'fifo')

    message = service.auto_link(transactions, asset=asset, algo=algo_type, year=year)

    return jsonify(message)


@blueprint.route('/auto_link_all_fifo', methods=['POST'])
@login_required
def auto_link_all_fifo():
    transactions = current_app.config['transactions']
    year_value = request.json.get('year', 'All Time') if request.json else 'All Time'
    service = AutoLinkService()
    selected_year = service.selected_year(year_value)

    result = service.auto_link_unlinked_sales(
        transactions,
        algo='fifo',
        year=selected_year,
        save_description="Added FIFO basis links from Auto Link guided action",
    )

    result['failures'] = [
        {
            'asset': failure.get('asset'),
            'unlinkable': failure.get('unlinkable'),
            'quantity': failure.get('quantity'),
            'timestamp': str(failure.get('timestamp')),
            'algo': failure.get('algo'),
        }
        for failure in result['failures']
    ]

    return jsonify(result)


@blueprint.route('/auto_link_pre_check', methods=['POST'])
@login_required
def auto_link_pre_check():

    # print(request.json)

    asset = request.json['row_data'][0]

    transactions = current_app.config['transactions']

    buys = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "buy"]
    sends = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "send"]
    receives = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "receive"]
    sells = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "sell"]

    buys.sort(key=lambda x: x.time_stamp)
    sends.sort(key=lambda x: x.time_stamp)
    receives.sort(key=lambda x: x.time_stamp)
    sells.sort(key=lambda x: x.time_stamp)

    auto_link_failures = _preview_auto_link_failures(asset, buys, sells, 'fifo')
    auto_link_failures.extend(_preview_auto_link_failures(asset, buys, sells, 'filo'))

    auto_link_check_failed = False

    if len(auto_link_failures) > 0:
        for i in auto_link_failures:
            if i['unlinkable'] > 0.000009:
                auto_link_check_failed = True

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
                            f" with a difference of {difference:.9f}. If the difference is a sell, add it under Import & Manage Data."
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


    # all sells linked to buys. Buys unlinked Quantity = holdings

    data = {}
    data['message'] = message
    data['auto_suggestions'] =  auto_suggestions['pre-check']

    holdings = "N/A"

    for a in transactions.asset_objects:
        if a.symbol != asset:
            continue

        # print(f"Asset Object symbol {a.symbol} Asset {asset} Holdings {a.holdings}")
        if a.holdings is not None:

            holdings = a.holdings

    if holdings == "N/A":
        data['auto_suggestions'].append([f"4.1.1", f"Holdings Provided {holdings}", "Not Complete"])
    else:
        data['auto_suggestions'].append([f"4.1.1", f"Holdings Provided {holdings}", "Complete"])

        expected_holdings = bought - sold
        holdings_difference = expected_holdings - holdings

        if holdings_difference > 0 or holdings_difference < 0:
            data['auto_suggestions'].append([f"4.1.2", f"Buys ({bought}) - sold ({sold}) = expected holdings ({expected_holdings}). expected holdings - declared holdings ({holdings}) = difference ({holdings_difference})", "Failed"])
        else:
            data['auto_suggestions'].append([f"4.1.2", f"Buys ({bought}) - sold ({sold}) = expected holdings ({expected_holdings}). expected holdings - declared holdings ({holdings}) = difference ({holdings_difference})", "passed"])


    return jsonify(data)






