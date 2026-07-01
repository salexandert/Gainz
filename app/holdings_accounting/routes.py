
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


def _all_crypto_assets(transactions):
    assets = set(getattr(transactions, "assets", set()) or set())
    assets.update(
        asset.symbol
        for asset in getattr(transactions, "asset_objects", []) or []
        if getattr(asset, "symbol", None)
    )
    return sorted(asset for asset in assets if asset not in FIAT_ASSET_SYMBOLS)


def _request_asset(payload):
    asset_data = payload.get("asset")
    if isinstance(asset_data, list) and asset_data:
        return str(asset_data[0]).upper()

    if isinstance(asset_data, str):
        return asset_data.upper()

    return ""


def _auto_link_failures_for_json(failures):
    rows = []
    for failure in failures or []:
        timestamp = failure.get("timestamp")
        if hasattr(timestamp, "strftime"):
            timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        rows.append({
            "asset": failure.get("asset", ""),
            "unlinked_quantity": format_quantity(failure.get("unlinkable", 0)),
            "sell_quantity": format_quantity(failure.get("quantity", 0)),
            "timestamp": str(timestamp or ""),
            "method": failure.get("algo", ""),
        })

    return rows


def _holdings_update_payload(transactions, asset, message, links_created=0, failures=None):
    stats_table_data = get_stats_table_data(transactions)
    return {
        "message": message,
        "links_created": links_created,
        "auto_link_failures": _auto_link_failures_for_json(failures),
        "stats_table_rows": _holdings_stats_rows(stats_table_data),
        "holdings_summary": _holdings_summary(transactions),
        "difference_breakdown": get_holdings_difference_breakdown(transactions, asset),
    }


def _holdings_bulk_payload(transactions, declared_holdings, zeroed_assets):
    stats_table_data = get_stats_table_data(transactions)
    holdings_text = ", ".join(
        f"{row['asset']} {format_quantity(row['quantity'])}" for row in declared_holdings
    )
    primary = declared_holdings[0]
    return {
        "message": (
            f"Saved current holdings: {holdings_text}; "
            f"all other tracked assets 0."
        ),
        "primary_asset": primary["asset"],
        "primary_quantity": format_quantity(primary["quantity"]),
        "declared_holdings": [
            {
                "asset": row["asset"],
                "quantity": format_quantity(row["quantity"]),
            }
            for row in declared_holdings
        ],
        "zeroed_assets": zeroed_assets,
        "stats_table_rows": _holdings_stats_rows(stats_table_data),
        "holdings_summary": _holdings_summary(transactions),
    }


def _bulk_holdings_from_payload(payload):
    rows = payload.get("holdings")
    if not isinstance(rows, list):
        rows = [
            {
                "asset": payload.get("primary_asset") or "BTC",
                "quantity": payload.get("primary_quantity") or 0,
            }
        ]

    holdings = []
    seen_assets = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            return None, f"Holdings row {index} is not valid."

        asset = str(row.get("asset") or "").strip().upper()
        quantity_value = row.get("quantity")

        if not asset and (quantity_value is None or str(quantity_value).strip() == ""):
            continue

        if not asset:
            return None, f"Enter an asset symbol for holdings row {index}."

        try:
            quantity = float(quantity_value)
        except (TypeError, ValueError):
            return None, f"Enter a valid current holdings quantity for {asset}."

        if quantity < 0:
            return None, f"Current holdings for {asset} cannot be negative."

        if asset in seen_assets:
            return None, f"{asset} appears more than once. Combine duplicate rows before saving."

        seen_assets.add(asset)
        holdings.append({"asset": asset, "quantity": quantity})

    if not holdings:
        return None, "Enter at least one current holding before saving."

    return holdings, None


@blueprint.route('/', methods=['POST', 'GET'])
@login_required
def holdings_accounting():
    transactions = current_app.config['transactions']
    guided_mode = str(request.args.get("guided") or "").lower() in ("1", "true", "yes")
    holdings_mode = str(request.args.get("mode") or "").lower()
    if holdings_mode not in ("declare", "reconcile"):
        holdings_mode = "declare" if guided_mode else "full"

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
        guided_mode=guided_mode,
        holdings_mode=holdings_mode,
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


@blueprint.route('/bulk_holdings', methods=['POST'])
@login_required
def bulk_holdings():
    payload = request.get_json(silent=True) or {}
    declared_holdings, error = _bulk_holdings_from_payload(payload)
    if error:
        return jsonify({"message": error}), 400

    transactions = current_app.config['transactions']
    assets = _all_crypto_assets(transactions)
    declared_by_asset = {row["asset"]: row["quantity"] for row in declared_holdings}
    for asset in declared_by_asset:
        if asset not in assets:
            assets.append(asset)
        assets.sort()

    zeroed_assets = []
    for asset in assets:
        if asset in declared_by_asset:
            transactions.set_holdings(asset, declared_by_asset[asset])
        else:
            transactions.set_holdings(asset, 0)
            zeroed_assets.append(asset)

    declared_names = ", ".join(row["asset"] for row in declared_holdings)
    transactions.save(description=f"Bulk holdings update: {declared_names} plus zero balances")

    return jsonify(
        _holdings_bulk_payload(
            transactions,
            declared_holdings,
            zeroed_assets,
        )
    )


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
    payload = request.get_json(silent=True) or {}
    asset = _request_asset(payload)

    try:
        amount_to_convert = float(payload.get('quantity') or 0)
    except (TypeError, ValueError):
        amount_to_convert = 0

    if not asset:
        return jsonify({"message": "Select an asset before classifying documented sends."}), 400

    if amount_to_convert <= 0:
        return jsonify({"message": "Enter a quantity greater than 0 before classifying documented sends."}), 400

    links_before = len(transactions.links)
    result_str = transactions.convert_sends_to_sells(asset=asset, amount_to_convert=amount_to_convert)
    failures = []

    if payload.get("auto_link", True):
        failures = transactions.auto_link(asset=asset, algo="fifo")

    links_created = max(len(transactions.links) - links_before, 0)
    transactions.save(description="Recorded documented sends as taxable disposals and ran FIFO")

    if links_created:
        result_str = f"{result_str} FIFO linked {links_created} basis lot(s)."

    if failures:
        result_str = (
            f"{result_str} {len(failures)} sale record(s) still need basis review."
        )

    return jsonify(
        _holdings_update_payload(
            transactions,
            asset,
            result_str,
            links_created=links_created,
            failures=failures,
        )
    )


@blueprint.route('/leave_basis_unresolved', methods=['POST'])
@login_required
def leave_basis_unresolved():
    transactions = current_app.config['transactions']
    payload = request.get_json(silent=True) or {}
    asset = _request_asset(payload)
    note = str(payload.get("note") or "").strip()
    gap_type = str(payload.get("gap_type") or "").strip().lower()
    if not note:
        note = "User will investigate source records later."

    if not asset:
        return jsonify({"message": "Select an asset before marking review status."}), 400

    transactions.set_basis_review_note(asset, status="needs_research", note=note)
    review_label = "holdings gap" if gap_type == "mismatch" else "basis review"
    transactions.save(description=f"Marked {asset} {review_label} as needs research")

    return jsonify(
        _holdings_update_payload(
            transactions,
            asset,
            f"{asset} {review_label} left unresolved as needs user research.",
        )
    )



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
