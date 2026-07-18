from . import blueprint
from flask import redirect, render_template, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from utils import *
from transactions import Transactions
import os
from datetime import datetime


def _current_transactions():
    transactions = current_app.config.get('transactions')
    if transactions is None:
        transactions = Transactions()
        current_app.config['transactions'] = transactions
    return transactions


def _format_modified_time(timestamp):
    if not timestamp:
        return "N/A"

    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %I:%M %p")


def _save_rows(transactions):
    saves = transactions.load_saves()
    current_view = os.path.abspath(getattr(transactions, "view", "") or "")
    rows = []

    for save in reversed(saves):
        save_path = os.path.abspath(save["value"])
        rows.append({
            "file": save["value"],
            "name": os.path.basename(save["value"]),
            "description": save.get("description") or "No description",
            "revision": save.get("revision_num") or "N/A",
            "modified": _format_modified_time(save.get("modified_time")),
            "is_current": save_path == current_view,
        })

    return rows


def _find_known_save(transactions, filename):
    requested = os.path.abspath(str(filename or ""))
    for save in transactions.load_saves():
        if os.path.abspath(save["value"]) == requested:
            return save

    return None


@blueprint.route('/',  methods=['GET'])
@login_required
def index():
    transactions = _current_transactions()
    return render_template(
        'history.html',
        history=_save_rows(transactions),
        restored=request.args.get("restored"),
    )

@blueprint.route('/bulk_classify', methods=['POST'])
@login_required
def bulk_classify():
    transactions = _current_transactions()
    asset = str(request.form.get("asset") or "").upper()
    from_type = request.form.get("from_type")
    to_type = request.form.get("to_type")

    count = 0
    if asset and from_type and to_type:
        for trans in transactions:
            if trans.symbol == asset and trans.trans_type.lower() == from_type.lower():
                trans.trans_type = to_type
                count += 1

        if count > 0:
            transactions.save(description=f"Bulk classified {count} {asset} {from_type}s to {to_type}")

    return redirect(url_for('history_blueprint.index'))


@blueprint.route('/compare_selected',  methods=['POST'])
@login_required
def compare_selected():

    data = request.json
    print("\n two rows")
    print(data['row_data']['0'])
    print(data['row_data']['1'])

    filename1 = data['row_data']['0'][0]
    filename2 = data['row_data']['1'][0]
    transactions1 = Transactions()
    transactions1.load(filename1)
    transactions2 = Transactions()
    transactions2.load(filename2)

    data = {}

    data['num_transactions'] = len(transactions1) - len(transactions2)

    num_buys = 0
    num_sells = 0
    num_links = 0
    total_purchased_quantity = 0.0
    total_purchased_unlinked_quantity = 0.0
    total_purchased_usd = 0.0
    total_sold_quantity = 0.0
    total_sold_unlinked_quantity = 0.0
    total_sold_usd = 0.0
    profit_loss_total = 0.0
    profit_loss_short = 0.0
    profit_loss_long = 0.0


    return jsonify(data)


@blueprint.route('/selected_save',  methods=['POST'])
@login_required
def selected_save():

    print(request.json['row_data'])

    filename = request.json['row_data'][0]
    # print(filename)

    transactions = Transactions()

    transactions.load(filename)

    links = set([
            link
            for trans in transactions
            for link in trans.links
            ])

    data = {}
    data['column_names'] = [
            "Symbol",
            "Total Purchased Quantity",
            "Total Purchased Unlinked Quantity",
            "Total Purchased USD",
            "Total Sold Quantity",
            "Total Sold Unlinked Quantity",
            "Total Sold USD",
            "Profit / Loss USD",
            "Total Sent Quantity",
            "Total Received Quantity",
            "Holdings"
        ]

    stats_table_data = []

    data['rows'] = stats_table_data

    for asset in transactions.assets:

        total_purchased_quantity = 0.0
        total_purchased_unlinked_quantity = 0.0
        total_purchased_usd = 0.0

        total_sold_quantity = 0.0
        total_sold_unlinked_quantity = 0.0
        total_sold_usd = 0.0

        total_sent_quantity = 0.0
        total_received_quantity = 0.0

        profit_loss = 0.0

        for link in links:
            if link.symbol == asset:
                profit_loss += link.profit_loss

        # set profit loss to total sold if all unlinked
        if profit_loss == 0.0:
            profit_loss = total_sold_usd

        for trans in transactions:
            if trans.symbol != asset:
                continue

            if trans.trans_type.lower() == "buy":
                total_purchased_quantity += trans.quantity
                total_purchased_unlinked_quantity += trans.unlinked_quantity
                total_purchased_usd += trans.tax_usd_total


            elif trans.trans_type.lower() == "sell":
                total_sold_quantity += trans.quantity
                total_sold_unlinked_quantity += trans.unlinked_quantity
                total_sold_usd += trans.tax_usd_total
                if trans.unlinked_quantity > 0:
                    profit_loss += trans.prorated_tax_usd(trans.unlinked_quantity)

            elif trans.trans_type.lower() == "send":
                total_sent_quantity += trans.quantity

            elif trans.trans_type.lower() == "receive":
                total_received_quantity += trans.quantity

            # print(f"Total Sold in usd: {total_sold_usd}")
            # print(f"Trans USD Total {trans.usd_total}")

        holdings = "N/A"

        for a in transactions.asset_objects:
            if a.symbol != asset:
                continue

            # print(f"Asset Object symbol {a.symbol} Asset {asset} Holdings {a.holdings}")
            if a.holdings is not None:
                holdings = a.holdings
                # print(f"Asset Object symbol {a.symbol} Asset {asset} Holdings {a.holdings}")

        total_sold_unlinked_quantity = round_decimals_down(total_sold_unlinked_quantity)
        if total_sold_unlinked_quantity != 0 and total_sold_unlinked_quantity < 0.0009:
            total_sold_unlinked_quantity = "Less than .0009"

        stats_table_data.append([
                f"{asset}",
                total_purchased_quantity,
                total_purchased_unlinked_quantity,
                "${:,.2f}".format(total_purchased_usd),
                 total_sold_quantity,
                total_sold_unlinked_quantity,
                "${:,.2f}".format(total_sold_usd),
                "${:,.2f}".format(profit_loss),
                total_sent_quantity,
                total_received_quantity,
                holdings

            ])


    return jsonify(data)


@blueprint.route('/selected_asset',  methods=['POST'])
@login_required
def selected_asset():

    filename = request.json['row_data'][0]

    transactions = Transactions()

    transactions.load(filename)

    date_range = {
            'start_date': '',
            'end_date': ''
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
        # source = None
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
                if link.holding_duration.days < 365:
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
            cost_basis += link.cost_basis

        proceeds = trans.tax_usd_total
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


    proceeds_total = 0
    cost_basis_total = 0
    gain_loss_total = 0
    for link in links:
        if link.holding_duration.days <= 365:
            continue


        proceeds_total  += link.proceeds
        cost_basis_total += link.cost_basis
        gain_loss_total += link.profit_loss

    data_dict = {}

    data_dict['detailed_stats'] = detailed_stats

    data_dict['sells_table_data'] = sales_table_data

    return jsonify(data_dict)

@blueprint.route('/load',  methods=['POST'])
@login_required
def load():

    transactions = _current_transactions()

    filename = request.json['data'][0]
    if not _find_known_save(transactions, filename):
        return jsonify({"error": "Choose a valid saved revision."}), 400

    transactions.load(filename)

    return jsonify("Revision loaded.")


@blueprint.route('/revert',  methods=['POST'])
@login_required
def revert():

    transactions = _current_transactions()

    data = request.get_json(silent=True) or {}
    filename = request.form.get("file")
    if not filename and data.get("data"):
        filename = data["data"][0]

    save = _find_known_save(transactions, filename)
    if not save:
        message = "Choose a valid saved revision to restore."
        if request.is_json:
            return jsonify({"error": message}), 400
        return redirect(url_for('history_blueprint.index', restored=message))

    transactions.load(save["value"])
    revision = save.get("revision_num") or "unknown"
    description = f"Restored revision {revision} from {os.path.basename(save['value'])}"
    restored_path = transactions.save(description)

    if request.is_json:
        return jsonify({
            "message": "Revision restored and saved as a new latest revision.",
            "restored_from": save["value"],
            "save_path": restored_path,
        })
    return redirect(url_for('history_blueprint.index', restored=description))


@blueprint.route('/delete',  methods=['POST'])
@login_required
def delete():

    transactions = current_app.config['transactions']

    filename = request.json['data'][0]
    transactions.delete(filename)

    transactions = Transactions()

    current_app.config['transactions'] = transactions

    return jsonify("Revision file moved aside and save list refreshed.")

@blueprint.route('/save',  methods=['POST'])
@login_required
def save():

    transactions = current_app.config['transactions']

    transactions.save()

    transactions = Transactions()

    current_app.config['transactions'] = transactions

    return jsonify("saved")

