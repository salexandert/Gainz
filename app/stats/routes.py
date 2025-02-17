from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from utils import *
from flask_wtf import FlaskForm
from wtforms.fields.html5 import DateTimeLocalField
from utils import *
from wtforms import SubmitField
from time import strftime




@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)    

    # Get Years
    years = set()
    for trans in transactions:
        years.add(trans.time_stamp.year)

    years = sorted(years)
    years.insert(0, 'All Time')
    
    return render_template('stats_page.html', stats_table_data=stats_table_data, date_range=date_range, years=years)


@blueprint.route('/selected_asset', methods=['POST'])
@login_required
def selected_asset():
    # Populate Links, Sells, Buys Tables based on selected asset from stats table

    # print(request.json)

    transactions = current_app.config['transactions']
    year = request.json['year']
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

    date_range = get_transactions_date_range(transactions, date_range)

    # get stats table data 
    stats_table_data = get_stats_table_data_range(transactions, date_range)

    # get stats for selected asset
    asset_stats = None
    for asset in stats_table_data:
        if asset['symbol'] == request.json['row_data'][0]:
            asset_stats = asset
            break 
    asset = asset_stats['symbol']

    # print(asset_stats)

    # Create detailed stats table data
    detailed_stats = [
        ["Quantity Purchased", asset_stats['total_purchased_quantity']],
        ["Number of Buys", asset_stats["num_buys"]],
        ["Number of Sells", asset_stats["num_sells"]],
        ["Number of Links", asset_stats["num_links"]],
        ["Average Buy Price", asset_stats["average_buy_price"]],
        ["Average Sell Price", asset_stats["average_sell_price"]],
        ["Quantity Sold", asset_stats['total_sold_quantity']],
        ["Quantity Sold Unlinked", asset_stats['total_sold_unlinked_quantity']],
        ["Quantity Purchased Unlinked", asset_stats['total_purchased_unlinked_quantity']],
        ["Quantity Purchased in USD", asset_stats['total_purchased_usd']],
        ["Quantity Sold in USD", asset_stats['total_sold_usd']],
        ["Profit / Loss in USD Total", asset_stats['profit_loss_total']],
        ["Profit / Loss in USD Short", asset_stats['profit_loss_short']],
        ["Profit / Loss in USD Long", asset_stats['profit_loss_long']],
        ["Quantity Sent", asset_stats['total_sent_quantity']],
        ["Quantity Received", asset_stats['total_received_quantity']],
    ]

    # Get Linked Table Data
    linked_table_data = get_linked_table_data(transactions, asset, date_range)

    # Get Sells Table Data 
    sells_table_data = get_sells_trans_table_data_range(transactions, asset, date_range)

    sells_unlinked_remaining = []
    if request.json['unlinked_remaining']:
        for sell in sells_table_data:
            if type(sell[4]) is str:
                continue

            if sell[4] > 0.000000009:
                sells_unlinked_remaining.append(sell)

        sells_table_data = sells_unlinked_remaining

    # Get Buys Table Data
    buys_table_data = get_buys_trans_table_data_range(transactions, asset, date_range)

    # Get All Links Table Data
    all_links_table_data = get_all_links_table_data(transactions, asset)

    data_dict = {}

    data_dict['all_links'] = all_links_table_data
    data_dict['detailed_stats'] = detailed_stats
    data_dict['linked'] = linked_table_data
    data_dict['sells'] = sells_table_data
    data_dict['buys'] = buys_table_data
    
    return jsonify(data_dict)


@blueprint.route('/date_range',  methods=['POST'])
@login_required
def date_range():

    # print(f" Date Range from stats page {request.json} ")

    transactions = current_app.config['transactions']

    year = request.json['year']

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
    
    date_range = get_transactions_date_range(transactions, date_range)
        
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
            row['profit_loss_total'],
            row['hodl']
        ])

    data = {}
    data['stats_table_rows'] = stats_table_rows

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
