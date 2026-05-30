from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from utils import *
from flask_wtf import FlaskForm
from wtforms.fields import DateTimeLocalField
from utils import *
from wtforms import SubmitField
from time import strftime


def _stats_table_rows(stats_table_data):
    return [
        [
            row['symbol'],
            row['total_purchased_quantity'],
            row['total_sold_quantity'],
            row['total_sold_unlinked_quantity'],
            row['total_purchased_unlinked_quantity'],
            row['total_purchased_usd'],
            row['total_sold_usd'],
            row.get('profit_loss_total', row.get('total_profit_loss')),
            row['hodl']
        ]
        for row in stats_table_data
    ]


def _stats_reconciliation_status(stats_table_data):
    assets_needing_links = [
        row['symbol']
        for row in stats_table_data
        if row.get('has_sells_without_links') or row.get('has_unlinked_sells')
    ]

    return {
        "is_reconciled": len(assets_needing_links) == 0,
        "assets_needing_links": assets_needing_links,
        "message": (
            "Not reconciled yet: sells exist without complete basis links. "
            "Run Auto Link, load a reconciled save, or review links before using these totals for tax filing."
            if assets_needing_links else ""
        )
    }


def _stats_import_warnings(transactions):
    return getattr(transactions, "import_warnings", [])


def _date_range_for_year(transactions, year):
    if year == 'All Time':
        date_range = {
            'start_date': '',
            'end_date': ''
        }
    else:
        date_range = {
            'start_date': f"01/01/{year} 12:00 AM",
            'end_date': f"12/31/{year} 11:59 PM"
        }

    return get_transactions_date_range(transactions, date_range)


def _has_unlinked_sales(stats_row):
    return bool(
        stats_row
        and (stats_row.get('has_sells_without_links') or stats_row.get('has_unlinked_sells'))
    )


def _holdings_reconciliation_rows(raw_holdings_rows, stats_table_data):
    stats_by_asset = {row['symbol']: row for row in stats_table_data}
    table_rows = []

    for row in raw_holdings_rows:
        row = list(row)
        asset = row[0]

        if _has_unlinked_sales(stats_by_asset.get(asset)):
            row[6] = "Unlinked sales"
            row[7] = "Run Auto Link or review basis links before relying on this asset's tax totals."

        table_rows.append(row)

    return table_rows


def _stats_summary(stats_table_data, raw_holdings_rows, import_warnings):
    assets_needing_hodl = sum(1 for row in raw_holdings_rows if row[1] == "N/A")
    assets_with_mismatches = sum(1 for row in raw_holdings_rows if row[6] == "Mismatch")
    unlinked_sales = sum(1 for row in stats_table_data if _has_unlinked_sales(row))
    import_warning_count = len(import_warnings or [])
    is_ready = (
        assets_needing_hodl == 0
        and assets_with_mismatches == 0
        and unlinked_sales == 0
        and import_warning_count == 0
    )

    return {
        "reconciliation": "Ready" if is_ready else "Not ready",
        "reconciliation_class": "status-matched" if is_ready else "status-mismatch",
        "assets_needing_hodl": assets_needing_hodl,
        "assets_with_mismatches": assets_with_mismatches,
        "import_warnings": import_warning_count,
        "unlinked_sales": unlinked_sales,
    }


@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    
    transactions = current_app.config['transactions']

    # Get Years
    years = set()
    for trans in transactions:
        years.add(trans.time_stamp.year)

    years = sorted(years)
    years.insert(0, 'All Time')
    
    all_time_range = get_transactions_date_range(transactions, {'start_date': '', 'end_date': ''})
    ranged_stats_table_data = get_stats_table_data_range(transactions, all_time_range)
    raw_holdings_reconciliation = get_multi_asset_holdings_reconciliation_table_data(transactions)
    import_warnings = _stats_import_warnings(transactions)

    return render_template(
        'stats_page.html',
        stats_table_data=ranged_stats_table_data,
        date_range=date_range,
        years=years,
        reconciliation_status=_stats_reconciliation_status(ranged_stats_table_data),
        import_warnings=import_warnings,
        stats_summary=_stats_summary(ranged_stats_table_data, raw_holdings_reconciliation, import_warnings),
        holdings_reconciliation_table_data=_holdings_reconciliation_rows(
            raw_holdings_reconciliation,
            ranged_stats_table_data,
        ),
    )


@blueprint.route('/selected_asset', methods=['POST'])
@login_required
def selected_asset():
    # Populate Links, Sells, Buys Tables based on selected asset from stats table

    # Debug logging
    current_app.logger.debug('Request JSON: %s', request.json)

    transactions = current_app.config['transactions']
    year = request.json.get('year')

    if year:
        date_range = _date_range_for_year(transactions, year)
    else:
        date_range = get_transactions_date_range(
            transactions,
            {
                'start_date': request.json.get('start_date', ''),
                'end_date': request.json.get('end_date', ''),
            },
        )

    # Debug logging
    current_app.logger.debug('Date Range: %s', date_range)

    # get stats table data 
    stats_table_data = get_stats_table_data_range(transactions, date_range)

    # Debug logging
    current_app.logger.debug('Stats Table Data: %s', stats_table_data)

    # get stats for selected asset
    asset_stats = None
    for asset in stats_table_data:
        if asset['symbol'] == request.json['row_data'][0]:
            asset_stats = asset
            break 
    asset = asset_stats['symbol']

    # Debug logging
    current_app.logger.debug('Asset Stats: %s', asset_stats)

    # Create detailed stats table data
    detailed_stats = [
        ["Total Gain", asset_stats['profit_loss_total']],
        ["Total Quantity Purchased", asset_stats['total_purchased_quantity']],
        ["Total Number of Buys", asset_stats["num_buys"]],
        ["Total Number of Sells", asset_stats["num_sells"]],
        ["Total Number of Links", asset_stats["num_links"]],
        ["Average Buy Price", asset_stats["average_buy_price"]],
        ["Average Sell Price", asset_stats["average_sell_price"]],
        ["Total Quantity Sold", asset_stats['total_sold_quantity']],
        ["Total Quantity Sold Unlinked", asset_stats['total_sold_unlinked_quantity']],
        ["Total Quantity Purchased Unlinked", asset_stats['total_purchased_unlinked_quantity']],
        ["Total Quantity Purchased in USD", asset_stats['total_purchased_usd']],
        ["Total Proceeds", asset_stats['total_sold_usd']],
        ["Short Proceeds", asset_stats['proceeds_short']],
        ["Short Cost Basis", asset_stats['cost_basis_short']],
        ["Short Gain", asset_stats['gain_short']],
        ["Long Proceeds", asset_stats['proceeds_long']],
        ["Long Cost Basis", asset_stats['cost_basis_long']],
        ["Long Gain", asset_stats['gain_long']],
        ["Total Quantity Sent", asset_stats['total_sent_quantity']],
        ["Total Quantity Received", asset_stats['total_received_quantity']],
    ]

    # Get Linked Table Data
    linked_table_data = get_linked_table_data(transactions, asset, date_range)

    # Get Sells Table Data 
    sells_table_data = get_sells_trans_table_data_range(transactions, asset, date_range)

    sells_unlinked_remaining = []
    if 'unlinked_remaining' in request.json and request.json['unlinked_remaining']:
        for sell in sells_table_data:
            if type(sell[4]) is str:
                continue

            if sell[4] > 0.000000009:
                sells_unlinked_remaining.append(sell)

        sells_table_data = sells_unlinked_remaining
    else:
        # handle the case where 'unlinked_remaining' is not present or False
        pass

    # Get Buys Table Data
    buys_table_data = get_buys_trans_table_data_range(transactions, asset, date_range)
    holdings_lot_table_data = get_current_holdings_lot_table_data(transactions, asset)
    holdings_reconciliation_data = get_holdings_reconciliation_summary(transactions, asset)
    chart_data = get_unrealized_chart_data(
        transactions,
        asset,
        request.json.get('current_usd_spot'),
    )

    # Get All Links Table Data
    all_links_table_data = get_all_links_table_data(transactions, asset)
    long_8949_table_data = []
    short_8949_table_data = []

    data_dict = {}

    data_dict['all_links'] = all_links_table_data
    data_dict['detailed_stats'] = detailed_stats
    data_dict['linked'] = linked_table_data
    data_dict['sells'] = sells_table_data
    data_dict['sells_table_data'] = sells_table_data
    data_dict['buys'] = buys_table_data
    data_dict['holdings_lot_table_data'] = holdings_lot_table_data
    data_dict['holdings_reconciliation_data'] = holdings_reconciliation_data
    raw_holdings_reconciliation = get_multi_asset_holdings_reconciliation_table_data(transactions)
    import_warnings = _stats_import_warnings(transactions)
    data_dict['holdings_reconciliation_table_data'] = _holdings_reconciliation_rows(
        raw_holdings_reconciliation,
        stats_table_data,
    )
    data_dict['unrealized_chart_data'] = chart_data["points"]
    data_dict['chart_current_usd_spot'] = chart_data["current_usd_spot"]
    data_dict['l8949_table_data'] = long_8949_table_data
    data_dict['s8949_table_data'] = short_8949_table_data
    data_dict['reconciliation_status'] = {
        "is_reconciled": not (asset_stats.get('has_sells_without_links') or asset_stats.get('has_unlinked_sells')),
        "message": (
            f"Not reconciled yet: {asset} has sells without complete basis links."
            if asset_stats.get('has_sells_without_links') or asset_stats.get('has_unlinked_sells')
            else ""
        )
    }
    data_dict['import_warnings'] = import_warnings
    data_dict['stats_summary'] = _stats_summary(stats_table_data, raw_holdings_reconciliation, import_warnings)
    
    return jsonify(data_dict)


@blueprint.route('/set_hodl', methods=['POST'])
@login_required
def set_hodl():
    transactions = current_app.config['transactions']
    asset = request.json['asset']
    quantity = request.json['quantity']
    year = request.json.get('year', 'All Time')
    current_usd_spot = request.json.get('current_usd_spot')

    if isinstance(asset, list):
        asset = asset[0]

    transactions.set_hodl(asset, quantity)
    save_path = transactions.save(description=f"Declared HODL for {asset}")
    date_range = _date_range_for_year(transactions, year)
    stats_table_data = get_stats_table_data_range(transactions, date_range)
    raw_holdings_reconciliation = get_multi_asset_holdings_reconciliation_table_data(transactions)
    import_warnings = _stats_import_warnings(transactions)
    chart_data = get_unrealized_chart_data(transactions, asset, current_usd_spot)

    return jsonify({
        "message": f"Declared HODL for {asset} saved.",
        "save_path": save_path,
        "asset": asset,
        "stats_table_rows": _stats_table_rows(stats_table_data),
        "stats_summary": _stats_summary(stats_table_data, raw_holdings_reconciliation, import_warnings),
        "holdings_reconciliation_table_data": _holdings_reconciliation_rows(
            raw_holdings_reconciliation,
            stats_table_data,
        ),
        "holdings_reconciliation_data": get_holdings_reconciliation_summary(transactions, asset),
        "holdings_lot_table_data": get_current_holdings_lot_table_data(transactions, asset),
        "unrealized_chart_data": chart_data["points"],
        "chart_current_usd_spot": chart_data["current_usd_spot"],
    })


@blueprint.route('/date_range',  methods=['POST'])
@login_required
def date_range():

    # print(f" Date Range from stats page {request.json} ")

    transactions = current_app.config['transactions']

    year = request.json.get('year')

    if year:
        date_range = _date_range_for_year(transactions, year)
    else:
        date_range = get_transactions_date_range(
            transactions,
            {
                'start_date': request.json.get('start_date', ''),
                'end_date': request.json.get('end_date', ''),
            },
        )
        
    stats_table_data = get_stats_table_data_range(transactions, date_range)
    raw_holdings_reconciliation = get_multi_asset_holdings_reconciliation_table_data(transactions)
    import_warnings = _stats_import_warnings(transactions)

    data = {}
    data['stats_table_rows'] = _stats_table_rows(stats_table_data)
    data['reconciliation_status'] = _stats_reconciliation_status(stats_table_data)
    data['import_warnings'] = import_warnings
    data['stats_summary'] = _stats_summary(stats_table_data, raw_holdings_reconciliation, import_warnings)
    data['holdings_reconciliation_table_data'] = _holdings_reconciliation_rows(
        raw_holdings_reconciliation,
        stats_table_data,
    )

    # convert dates back to string format
    date_range['start_date'] = datetime.datetime.strftime(date_range['start_date'], "%Y-%m-%d %H:%M")
    date_range['end_date'] = datetime.datetime.strftime(date_range['end_date'], "%Y-%m-%d %H:%M")
    
    data['date_range'] = date_range

    return jsonify(data)



@blueprint.route('/linkable_data', methods=['POST'])
@login_required
def linkable_data():
    
    # print(request.json)
    transactions = current_app.config['transactions']

    # Get selected Trans Object
    row_data = request.json['row_data']
    trans1_name = row_data[0]
    for trans in transactions:
        # print(trans.name)
        if trans.name == trans1_name:
            # print(f"Trans1 Found {trans.name}")
            trans1_obj = trans
            break

    linked_table_data = get_linked_table_data(transactions, trans1_obj)
    linkable_table_data = get_linkable_table_data(transactions, trans1_obj)

    data_dict = {}
    data_dict['linked'] = linked_table_data
    data_dict['linkable'] = linkable_table_data
    

    return jsonify(data_dict)
