import datetime

from . import blueprint
from flask import current_app, jsonify, render_template, request
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms.fields import DateTimeLocalField

from utils import *


class StatsDateRange(FlaskForm):
    start = DateTimeLocalField('Start', format='%Y-%m-%dT%H:%M')
    end = DateTimeLocalField('End', format='%Y-%m-%dT%H:%M')
    submit = SubmitField('Submit')


def _parse_model_number(value, default=None):
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip().replace('$', '').replace(',', '')
    if value == '':
        return default

    return float(value)


def _format_model_currency(value):
    return "${:,.2f}".format(float(value or 0))


def _format_model_quantity(value):
    return format_quantity(float(value or 0))


def _model_lot_datetime(lot):
    acquired_at = lot["acquired_at"]
    if hasattr(acquired_at, "tzinfo") and acquired_at.tzinfo is not None:
        acquired_at = acquired_at.replace(tzinfo=None)

    return acquired_at


def _model_term(acquired_at, sale_date):
    return "Long" if (sale_date - acquired_at).days > 365 else "Short"


def _model_sale_row(lot, quantity, sale_usd_spot, sale_date):
    acquired_at = _model_lot_datetime(lot)
    proceeds = quantity * sale_usd_spot
    cost_basis = quantity * lot["usd_spot"]
    gain_or_loss = proceeds - cost_basis

    return [
        lot["source"],
        lot["asset"],
        datetime.datetime.strftime(acquired_at, "%Y-%m-%d %H:%M:%S"),
        _format_model_quantity(lot["original_quantity"]),
        _format_model_quantity(lot["estimated_held_quantity"]),
        _format_model_quantity(quantity),
        _format_model_currency(lot["usd_spot"]),
        _format_model_currency(proceeds),
        _format_model_currency(cost_basis),
        _format_model_currency(gain_or_loss),
        _model_term(acquired_at, sale_date),
    ]


def _build_model_sale_batch(lots, target_quantity, sale_usd_spot, sale_date):
    rows = []
    quantity_total = 0.0
    proceeds_total = 0.0
    cost_basis_total = 0.0
    gain_loss_total = 0.0
    long_gain_loss = 0.0
    short_gain_loss = 0.0
    long_quantity = 0.0
    short_quantity = 0.0
    remaining_quantity = target_quantity

    for lot in lots:
        if remaining_quantity <= 0.000000001:
            break

        available_quantity = float(lot["estimated_held_quantity"])
        if available_quantity <= 0.000000001:
            continue

        quantity = min(available_quantity, remaining_quantity)
        acquired_at = _model_lot_datetime(lot)
        proceeds = quantity * sale_usd_spot
        cost_basis = quantity * lot["usd_spot"]
        gain_or_loss = proceeds - cost_basis
        term = _model_term(acquired_at, sale_date)

        rows.append(_model_sale_row(lot, quantity, sale_usd_spot, sale_date))

        quantity_total += quantity
        proceeds_total += proceeds
        cost_basis_total += cost_basis
        gain_loss_total += gain_or_loss
        if term == "Long":
            long_quantity += quantity
            long_gain_loss += gain_or_loss
        else:
            short_quantity += quantity
            short_gain_loss += gain_or_loss

        remaining_quantity -= quantity

    summary = {
        "quantity": quantity_total,
        "quantity_display": _format_model_quantity(quantity_total),
        "proceeds": proceeds_total,
        "proceeds_display": _format_model_currency(proceeds_total),
        "cost_basis": cost_basis_total,
        "cost_basis_display": _format_model_currency(cost_basis_total),
        "gain_loss": gain_loss_total,
        "gain_loss_display": _format_model_currency(gain_loss_total),
        "long_quantity_display": _format_model_quantity(long_quantity),
        "long_gain_loss_display": _format_model_currency(long_gain_loss),
        "short_quantity_display": _format_model_quantity(short_quantity),
        "short_gain_loss_display": _format_model_currency(short_gain_loss),
        "remaining_quantity": max(remaining_quantity, 0.0),
        "remaining_quantity_display": _format_model_quantity(max(remaining_quantity, 0.0)),
        "fully_covered": remaining_quantity <= 0.000000001,
    }

    return {
        "rows": rows,
        "summary": summary,
    }


def _current_model_lots(transactions, asset):
    return [
        lot for lot in get_current_holdings_lots(transactions, asset)
        if lot["asset"] == asset and float(lot["estimated_held_quantity"]) > 0.000000001
    ]


def _model_sale_payload(transactions, asset, sale_usd_spot, quantity=None, total_in_usd=None):
    sale_usd_spot = float(sale_usd_spot)
    if sale_usd_spot <= 0:
        raise ValueError("Enter a USD spot price greater than zero.")

    if quantity is None:
        if total_in_usd is None or float(total_in_usd) <= 0:
            raise ValueError("Enter either a sale quantity or a total sale amount in USD.")
        total_in_usd = float(total_in_usd)
        quantity = total_in_usd / sale_usd_spot
    else:
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError("Enter a sale quantity greater than zero.")
        total_in_usd = quantity * sale_usd_spot

    sale_date = datetime.datetime.now()
    lots = _current_model_lots(transactions, asset)
    declared_holdings = transactions.get_holdings(asset)
    available_quantity = sum(float(lot["estimated_held_quantity"]) for lot in lots)
    warnings = []

    if declared_holdings is None:
        warnings.append(
            "No declared holdings are saved for this asset, so Gainz is modeling from all available buy/receive lots."
        )

    if available_quantity + 0.000000001 < quantity:
        warnings.append(
            f"Only {_format_model_quantity(available_quantity)} {asset} is available in current modeled lots, "
            f"so this sale cannot be fully covered."
        )

    long_lots = [
        lot for lot in lots
        if _model_term(_model_lot_datetime(lot), sale_date) == "Long"
    ]
    short_lots = [
        lot for lot in lots
        if _model_term(_model_lot_datetime(lot), sale_date) == "Short"
    ]

    strategy_specs = [
        (
            "fifo",
            "FIFO / Oldest Current Lots",
            sorted(lots, key=lambda lot: _model_lot_datetime(lot)),
        ),
        (
            "fewest_lots",
            "Fewest Lots",
            sorted(lots, key=lambda lot: lot["estimated_held_quantity"], reverse=True),
        ),
        (
            "min_gain",
            "Lowest Gain / Highest Basis",
            sorted(lots, key=lambda lot: lot["usd_spot"], reverse=True),
        ),
        (
            "max_gain",
            "Highest Gain / Lowest Basis",
            sorted(lots, key=lambda lot: lot["usd_spot"]),
        ),
        (
            "min_gain_long",
            "Lowest Gain, Long-Term Lots",
            sorted(long_lots, key=lambda lot: lot["usd_spot"], reverse=True),
        ),
        (
            "max_gain_long",
            "Highest Gain, Long-Term Lots",
            sorted(long_lots, key=lambda lot: lot["usd_spot"]),
        ),
        (
            "min_gain_short",
            "Lowest Gain, Short-Term Lots",
            sorted(short_lots, key=lambda lot: lot["usd_spot"], reverse=True),
        ),
        (
            "max_gain_short",
            "Highest Gain, Short-Term Lots",
            sorted(short_lots, key=lambda lot: lot["usd_spot"]),
        ),
    ]

    batches_by_key = {}
    batch_options = []
    for key, label, strategy_lots in strategy_specs:
        batch = _build_model_sale_batch(strategy_lots, quantity, sale_usd_spot, sale_date)
        if not batch["rows"]:
            continue

        batch["key"] = key
        batch["label"] = label
        batches_by_key[key] = batch
        batch_options.append({
            "key": key,
            "label": label,
            "fully_covered": batch["summary"]["fully_covered"],
        })

    all_lot_rows = [
        _model_sale_row(lot, lot["estimated_held_quantity"], sale_usd_spot, sale_date)
        for lot in sorted(lots, key=lambda lot: _model_lot_datetime(lot))
    ]

    default_batch_key = "fifo" if "fifo" in batches_by_key else (batch_options[0]["key"] if batch_options else "")

    return {
        "asset": asset,
        "sale_usd_spot": sale_usd_spot,
        "sale_usd_spot_display": _format_model_currency(sale_usd_spot),
        "potential_sale_quantity": quantity,
        "potential_sale_quantity_display": _format_model_quantity(quantity),
        "total_in_usd": _format_model_currency(total_in_usd),
        "declared_holdings": (
            _format_model_quantity(declared_holdings)
            if declared_holdings is not None
            else "N/A"
        ),
        "available_quantity": _format_model_quantity(available_quantity),
        "warnings": warnings,
        "batch_options": batch_options,
        "batches_by_key": batches_by_key,
        "default_batch_key": default_batch_key,
        "all_linkable_buys_datatable": all_lot_rows,
    }


@blueprint.route('/', methods=['GET', 'POST'])
@login_required
def index():
    date_range = StatsDateRange()
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)

    return render_template('model.html', stats_table_data=stats_table_data, date_range=date_range)


@blueprint.route('/selected_asset', methods=['POST'])
@login_required
def selected_asset():
    transactions = current_app.config['transactions']
    row_data = request.json.get('row_data') or []
    if not row_data:
        return jsonify({"error": "Select an asset first."}), 400

    try:
        payload = _model_sale_payload(
            transactions=transactions,
            asset=row_data[0],
            sale_usd_spot=_parse_model_number(request.json.get('usd_spot')),
            quantity=_parse_model_number(request.json.get('quantity')),
            total_in_usd=_parse_model_number(request.json.get('total_in_usd')),
        )
    except (TypeError, ValueError) as error:
        current_app.logger.info("Invalid model sale request: %s", error)
        return jsonify({
            "error": "Check the selected asset, sale quantity, and USD price before modeling this sale."
        }), 400

    return jsonify(payload)


@blueprint.route('/date_range', methods=['POST'])
@login_required
def date_range():
    transactions = current_app.config['transactions']

    date_range = get_transactions_date_range(transactions, {
        'start_date': request.json['start_date'],
        'end_date': request.json['end_date'],
    })

    stats_table_data = get_stats_table_data_range(transactions, date_range)
    stats_table_rows = []
    for row in stats_table_data:
        stats_table_rows.append([
            row['symbol'],
            row['total_purchased_quantity'],
            row['total_sold_quantity'],
            row['total_sold_unlinked_quantity'],
            row['total_purchased_unlinked_quantity'],
            row['total_purchased_usd'],
            row['total_sold_usd'],
            row.get('profit_loss_total', row.get('total_profit_loss')),
            row['holdings'],
        ])

    data = {}
    data['stats_table_rows'] = stats_table_rows
    data['date_range'] = {
        'start_date': datetime.datetime.strftime(date_range['start_date'], "%Y-%m-%d %H:%M"),
        'end_date': datetime.datetime.strftime(date_range['end_date'], "%Y-%m-%d %H:%M"),
    }

    return jsonify(data)


@blueprint.route('/linkable_data', methods=['POST'])
@login_required
def linkable_data():
    transactions = current_app.config['transactions']

    row_data = request.json['row_data']
    trans1_obj = None
    for trans in transactions:
        if trans.name == row_data[0]:
            trans1_obj = trans
            break

    if trans1_obj is None:
        return jsonify({"linked": [], "linkable": []})

    data_dict = {}
    data_dict['linked'] = get_linked_table_data(transactions, trans1_obj)
    data_dict['linkable'] = get_linkable_table_data(transactions, trans1_obj)

    return jsonify(data_dict)
