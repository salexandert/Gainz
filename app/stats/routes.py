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
    for link in transactions.links:
        years.add(link.sell.time_stamp.year)

    years = sorted(years)
    years.insert(0, 'All Time')
    
    return render_template('stats_page.html', stats_table_data=stats_table_data, date_range=date_range, years=years)


@blueprint.route('/selected_asset',  methods=['POST'])
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
        ["Profit / Loss in USD", asset_stats['total_profit_loss']],
        ["Quantity Sent", asset_stats['total_sent_quantity']],
        ["Quantity Received", asset_stats['total_received_quantity']],
    ]

    # # Get Linked Table Data
    # linked_table_data = get_linked_table_data(transactions, asset, date_range)

    # Sells table 
    start_date = date_range['start_date']
    end_date = date_range['end_date']
                                                                
    # Filter Transactions to date range
    filtered_transactions = []
    for trans in transactions:
        if trans.symbol != asset:
            continue

        if start_date and not end_date:
            if trans.time_stamp >= start_date:
                filtered_transactions.append(trans)

        elif not start_date and end_date:
            if trans.time_stamp <= end_date:
                filtered_transactions.append(trans)

        elif start_date and end_date:
            if trans.time_stamp >= start_date and trans.time_stamp <= end_date:              
                filtered_transactions.append(trans)


    # Get Sales Table 
    sales_table_data = []
    proceeds_total = 0
    cost_basis_total = 0
    gain_loss_total = 0
    for trans in filtered_transactions:
        
        description = f"{trans.quantity} of {trans.symbol}"
        acquired = None
        sold_date = None
        proceeds = None 
        cost_basis = 0
        source = None
        gain_loss = 0

        if trans.trans_type != "sell":
            continue
        
        if type(year) == int:
            if trans.time_stamp.year != int(year):
                continue
        
        if len(trans.links) == 0:
            continue
        
        elif len(trans.links) > 1:
            acquired = "Multiple Dates"
            all_short = True
            all_long = True
            
            for link in trans.links:

                gain_loss += link.profit_loss
                if link.hodl_duration.days < 365:
                    all_long = False
                else:
                    all_short = False
            
            if all_long is False and all_short is False:
                acquired += " Long and Short"

            elif all_long is True:
                acquired += " All Long"
            
            elif all_short is True:
                acquired += " All Short"
     
        else:
            gain_loss = trans.links[0].profit_loss
            acquired = trans.links[0].buy.time_stamp
    
        for link in trans.links:
            cost_basis += link.cost_basis + link.buy.fee
    
        proceeds = trans.usd_total - float(trans.fee)
        gain_loss = proceeds - cost_basis
        sold_date = trans.time_stamp

        proceeds_total  += proceeds
        cost_basis_total += cost_basis
        gain_loss_total += gain_loss
        
        sales_table_data.append([
            description,
            acquired,
            sold_date,
            "${:,.2f}".format(proceeds),           
            "${:,.2f}".format(cost_basis),
            "${:,.2f}".format(gain_loss),
            trans.source])
    
    sales_table_data.insert(0, [
        "Totals",
        "",
        "",
        "${:,.2f}".format(proceeds_total),           
        "${:,.2f}".format(cost_basis_total),
        "${:,.2f}".format(gain_loss_total),
        ""
    ])

    
    # Get links
    links = set([
            link 
            for trans in filtered_transactions
            for link in trans.links
            ])
    
    # Get 8949 Long
    s8949_table_data = []
    proceeds_total = 0
    cost_basis_total = 0
    gain_loss_total = 0
    for link in links:
        if link.hodl_duration.days <= 365:
            continue


        proceeds_total  += link.proceeds
        cost_basis_total += link.cost_basis
        gain_loss_total += link.profit_loss
        s8949_table_data.append([
            f"{link.quantity} of {link.symbol}",
            link.buy.time_stamp,
            link.sell.time_stamp,
            "${:,.2f}".format(link.proceeds),           
            "${:,.2f}".format(link.cost_basis),
            "${:,.2f}".format(link.profit_loss),
            link.buy.source
            
        ])
    s8949_table_data.insert(0, [
        "Totals",
        "",
        "",
        "${:,.2f}".format(proceeds_total),           
        "${:,.2f}".format(cost_basis_total),
        "${:,.2f}".format(gain_loss_total),
        ""
    ])

    # Get 8949 Short
    l8949_table_data = []
    proceeds_total = 0
    cost_basis_total = 0
    gain_loss_total = 0
    for link in links:
        if link.hodl_duration.days > 365:
            continue

        proceeds_total  += link.proceeds
        cost_basis_total += link.cost_basis
        gain_loss_total += link.profit_loss
        l8949_table_data.append([
            f"{link.quantity} of {link.symbol}",
            link.buy.time_stamp,
            link.sell.time_stamp,
            "${:,.2f}".format(link.proceeds),           
            "${:,.2f}".format(link.cost_basis),
            "${:,.2f}".format(link.profit_loss),
            link.buy.source
            
        ])
    l8949_table_data.insert(0, [
        "Totals",
        "",
        "",
        "${:,.2f}".format(proceeds_total),           
        "${:,.2f}".format(cost_basis_total),
        "${:,.2f}".format(gain_loss_total),
        ""
    ])
    


    # Chart Data
    start_date = date_range['start_date']
    end_date = date_range['end_date']
  
                                                                                                                      
    # Filter Transactions to date range
    filtered_transactions = []
    for trans in transactions:
        if trans.symbol != asset:
            continue

        if start_date and not end_date:
            if trans.time_stamp >= start_date:
                filtered_transactions.append(trans)

        elif not start_date and end_date:
            if trans.time_stamp <= end_date:
                filtered_transactions.append(trans)

        elif start_date and end_date:
            if trans.time_stamp >= start_date and trans.time_stamp <= end_date:              
                filtered_transactions.append(trans)


    unrealized_chart_data = []

    to_date_quantity = 0.0
    to_date_usd_total = 0.0
    filtered_transactions.sort(key=lambda x: x.time_stamp)
    for trans in filtered_transactions:

        if trans.trans_type == 'buy':
        
            to_date_quantity += trans.quantity
            to_date_usd_total += trans.usd_total
            gain_loss = (to_date_quantity * trans.usd_spot) - to_date_usd_total
            to_date_profit = (to_date_quantity * trans.usd_spot)

            unrealized_chart_data.append({
                'x': datetime.datetime.strftime(trans.time_stamp, "%Y-%m-%d %H:%M:%S"), 
                'y': to_date_profit, 
                'quantity': to_date_quantity, 
                'usd_spot': "${:,.2f}".format(trans.usd_spot),
                'cost_baisis': "${:,.2f}".format(to_date_usd_total),
                'gain_loss': "${:,.2f}".format(gain_loss)
                })

        elif trans.trans_type == 'sell':

            to_date_quantity -= trans.quantity
            to_date_usd_total -= trans.usd_total
            gain_loss = (to_date_quantity * trans.usd_spot) - to_date_usd_total
            to_date_profit = (to_date_quantity * trans.usd_spot)

            unrealized_chart_data.append({
                'x': datetime.datetime.strftime(trans.time_stamp, "%Y-%m-%d %H:%M:%S"), 
                'y': to_date_profit, 
                'quantity': to_date_quantity, 
                'usd_spot':  "${:,.2f}".format(trans.usd_spot),
                'cost_baisis': "${:,.2f}".format(to_date_usd_total),
                'gain_loss': "${:,.2f}".format(gain_loss)
                })

    if 'current_usd_spot' in request.json:
        usd_spot = float(request.json['current_usd_spot'].replace(',', ''))
        to_date_profit = (to_date_quantity * usd_spot)
        gain_loss = (to_date_quantity * usd_spot) - to_date_usd_total
        
        unrealized_chart_data.append({
                'x': strftime("%Y-%m-%d %H:%M:%S"), 
                'y': to_date_profit, 
                'quantity': to_date_quantity, 
                'usd_spot':  "${:,.2f}".format(usd_spot),
                'cost_baisis': "${:,.2f}".format(to_date_usd_total),
                'gain_loss': "${:,.2f}".format(gain_loss)
                })

    data_dict = {}

    data_dict['detailed_stats'] = detailed_stats
    data_dict['s8949_table_data'] = s8949_table_data
    data_dict['l8949_table_data'] = l8949_table_data
    data_dict['sells_table_data'] = sales_table_data
    data_dict['unrealized_chart_data'] = unrealized_chart_data

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
            row['total_profit_loss'],
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
