import datetime
from transaction import Transaction
from dateutil.tz import tzutc
import requests
import datetime
import os
import math
from decimal import Decimal, ROUND_FLOOR
from dateutil import parser
from dateutil.tz import gettz

os.environ['REQUESTS_CA_BUNDLE'] = "certifi/cacert.pem"

# Define the timezone information
tzinfos = {
    'PDT': gettz('America/Los_Angeles'),
    'PST': gettz('America/Los_Angeles'),
    # Add other timezones as needed
}

FIAT_ASSET_SYMBOLS = {"USD"}
FORM_8949_COLUMNS = [
    "description",
    "date_acquired",
    "date_sold",
    "proceeds",
    "cost_basis",
    "gain_loss",
    "source",
    "asset",
    "quantity",
    "term",
]


def format_quantity(quantity, decimals=8):
    """Format crypto quantities without exposing floating-point noise."""
    if isinstance(quantity, str):
        return quantity

    try:
        value = Decimal(str(quantity))
    except Exception:
        return quantity

    if value == 0:
        return "0"

    quantizer = Decimal("1").scaleb(-decimals)
    value = value.quantize(quantizer)
    text = format(value, "f").rstrip("0").rstrip(".")
    return text or "0"


def parse_float_value(value):
    if value is None or value == "":
        return None

    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def comparable_datetime(value):
    if hasattr(value, "replace") and getattr(value, "tzinfo", None):
        return value.replace(tzinfo=None)

    return value


def currency(value):
    return "${:,.2f}".format(value)


def _format_report_datetime(value):
    if hasattr(value, "strftime"):
        return datetime.datetime.strftime(value, "%Y-%m-%d %H:%M:%S")

    return value


def _date_in_range(value, date_range):
    if not date_range:
        return True

    start_date = date_range.get("start_date")
    end_date = date_range.get("end_date")
    value = comparable_datetime(value)

    if start_date:
        start_date = comparable_datetime(start_date)
        if value < start_date:
            return False

    if end_date:
        end_date = comparable_datetime(end_date)
        if value > end_date:
            return False

    return True


def _transaction_fee(transaction):
    fee = getattr(transaction, "fee", None)
    return float(fee) if fee is not None else 0.0


def _prorated_fee(transaction, quantity):
    if not getattr(transaction, "quantity", 0):
        return 0.0

    return _transaction_fee(transaction) * (float(quantity) / float(transaction.quantity))


def is_long_term_link(link):
    return link.holding_duration.days > 365


def get_taxable_links(transactions, asset=None, date_range=None):
    taxable_links = []

    for link in getattr(transactions, "links", []):
        if not hasattr(link, "sell") or not hasattr(link, "buy"):
            continue

        if asset and link.symbol != asset:
            continue

        if not _date_in_range(link.sell.time_stamp, date_range):
            continue

        taxable_links.append(link)

    return sorted(
        taxable_links,
        key=lambda link: (
            comparable_datetime(link.sell.time_stamp),
            comparable_datetime(link.buy.time_stamp),
            link.symbol,
            link.id,
        ),
    )


def get_form_8949_report_rows(transactions, asset=None, date_range=None, term=None):
    rows = []

    for link in get_taxable_links(transactions, asset=asset, date_range=date_range):
        link_term = "long" if is_long_term_link(link) else "short"
        if term and link_term != term:
            continue

        sell_fee = _prorated_fee(link.sell, link.quantity)
        buy_fee = _prorated_fee(link.buy, link.quantity)
        proceeds = link.proceeds - sell_fee
        cost_basis = link.cost_basis + buy_fee
        gain_loss = proceeds - cost_basis

        rows.append({
            "description": f"Crypto {link.symbol}",
            "date_acquired": link.buy.time_stamp,
            "date_sold": link.sell.time_stamp,
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "gain_loss": gain_loss,
            "source": link.sell.source,
            "asset": link.symbol,
            "quantity": link.quantity,
            "term": link_term,
            "link_id": link.id,
            "buy_uid": getattr(link.buy, "uid", ""),
            "sell_uid": getattr(link.sell, "uid", ""),
            "year": link.sell.time_stamp.year,
        })

    return rows


def get_form_8949_totals(transactions, asset=None, date_range=None):
    totals = {
        "short": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
        "long": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
        "total": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
    }

    for row in get_form_8949_report_rows(transactions, asset=asset, date_range=date_range):
        for bucket in (row["term"], "total"):
            totals[bucket]["rows"] += 1
            totals[bucket]["proceeds"] += row["proceeds"]
            totals[bucket]["cost_basis"] += row["cost_basis"]
            totals[bucket]["gain_loss"] += row["gain_loss"]

    return totals


def get_form_8949_table_data(transactions, asset=None, date_range=None, term=None):
    return [
        [
            row["description"],
            _format_report_datetime(row["date_acquired"]),
            _format_report_datetime(row["date_sold"]),
            currency(row["proceeds"]),
            currency(row["cost_basis"]),
            currency(row["gain_loss"]),
            row["source"],
        ]
        for row in get_form_8949_report_rows(
            transactions,
            asset=asset,
            date_range=date_range,
            term=term,
        )
    ]


def get_sales_report_rows(transactions, asset=None, date_range=None):
    links_by_sell = {}

    for link in get_taxable_links(transactions, asset=asset, date_range=date_range):
        links_by_sell.setdefault(link.sell.uid, {"sell": link.sell, "links": []})
        links_by_sell[link.sell.uid]["links"].append(link)

    rows = []
    for group in sorted(
        links_by_sell.values(),
        key=lambda group: comparable_datetime(group["sell"].time_stamp),
    ):
        sell = group["sell"]
        links = sorted(group["links"], key=lambda link: comparable_datetime(link.buy.time_stamp))
        linked_quantity = sum(link.quantity for link in links)
        proceeds = 0.0
        cost_basis = 0.0
        long_count = 0
        short_count = 0

        for link in links:
            proceeds += link.proceeds - _prorated_fee(link.sell, link.quantity)
            cost_basis += link.cost_basis + _prorated_fee(link.buy, link.quantity)
            if is_long_term_link(link):
                long_count += 1
            else:
                short_count += 1

        if len(links) == 1:
            acquired = links[0].buy.time_stamp
        elif long_count and short_count:
            acquired = "Multiple Dates Long and Short"
        elif long_count:
            acquired = "Multiple Dates All Long"
        else:
            acquired = "Multiple Dates All Short"

        rows.append({
            "description": f"{format_quantity(linked_quantity)} of {sell.symbol}",
            "date_acquired": acquired,
            "date_sold": sell.time_stamp,
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "gain_loss": proceeds - cost_basis,
            "source": sell.source,
            "asset": sell.symbol,
            "linked_quantity": linked_quantity,
            "sell_quantity": sell.quantity,
            "unlinked_quantity": sell.unlinked_quantity,
            "year": sell.time_stamp.year,
        })

    return rows


def get_sales_report_table_data(transactions, asset=None, date_range=None):
    return [
        [
            row["description"],
            _format_report_datetime(row["date_acquired"]),
            _format_report_datetime(row["date_sold"]),
            currency(row["proceeds"]),
            currency(row["cost_basis"]),
            currency(row["gain_loss"]),
            row["source"],
        ]
        for row in get_sales_report_rows(transactions, asset=asset, date_range=date_range)
    ]


def _stats_row_has_unlinked_sales(row):
    return bool(
        row.get("has_sells_without_links")
        or row.get("has_unlinked_sells")
        or (
            row.get("num_sells", 0) > 0
            and row.get("num_links", 0) == 0
        )
    )


def get_audit_readiness_summary(transactions):
    if len(getattr(transactions, "transactions", [])) == 0:
        stats_rows = []
    else:
        date_range = get_transactions_date_range(transactions, {"start_date": "", "end_date": ""})
        stats_rows = get_stats_table_data_range(transactions, date_range)
    holdings_rows = get_multi_asset_holdings_reconciliation_table_data(transactions)
    form_8949_totals = get_form_8949_totals(transactions)
    import_warnings = getattr(transactions, "import_warnings", []) or []

    assets_with_unlinked_sales = [
        row["symbol"]
        for row in stats_rows
        if _stats_row_has_unlinked_sales(row)
    ]
    assets_needing_holdings = [
        row[0]
        for row in holdings_rows
        if row[6] == "Needs declared holdings"
    ]
    assets_with_mismatches = [
        row[0]
        for row in holdings_rows
        if row[6] == "Mismatch"
    ]
    blockers = []
    warnings = []

    if len(getattr(transactions, "transactions", [])) == 0:
        blockers.append("Import transactions before generating an audit packet.")

    if assets_with_unlinked_sales:
        blockers.append(
            "Complete basis links for: " + ", ".join(assets_with_unlinked_sales)
        )

    if assets_needing_holdings:
        blockers.append(
            "Declare current holdings for: " + ", ".join(assets_needing_holdings)
        )

    if assets_with_mismatches:
        blockers.append(
            "Resolve holdings mismatches for: " + ", ".join(assets_with_mismatches)
        )

    if import_warnings:
        warnings.append(
            f"Review {len(import_warnings)} import warning"
            f"{'s' if len(import_warnings) != 1 else ''}."
        )

    if form_8949_totals["total"]["rows"] == 0 and any(row.get("num_sells", 0) > 0 for row in stats_rows):
        blockers.append("Sells exist, but no linked Form 8949 rows are ready.")

    is_ready = len(blockers) == 0 and len(warnings) == 0

    if blockers:
        status = "Not ready"
        status_class = "status-mismatch"
        next_action = blockers[0]
    elif warnings:
        status = "Review warnings"
        status_class = "status-unlinked-sales"
        next_action = warnings[0]
    else:
        status = "Ready"
        status_class = "status-matched"
        next_action = "Generate the audit packet and review the exported files."

    return {
        "status": status,
        "status_class": status_class,
        "is_ready": is_ready,
        "next_action": next_action,
        "blockers": blockers,
        "warnings": warnings,
        "import_warnings": import_warnings,
        "metrics": {
            "transactions": len(getattr(transactions, "transactions", [])),
            "assets": len(getattr(transactions, "assets", set())),
            "links": len(getattr(transactions, "links", set())),
            "assets_needing_holdings": len(assets_needing_holdings),
            "assets_with_mismatches": len(assets_with_mismatches),
            "assets_with_unlinked_sales": len(assets_with_unlinked_sales),
            "import_warnings": len(import_warnings),
            "form_8949_rows": form_8949_totals["total"]["rows"],
            "form_8949_proceeds": currency(form_8949_totals["total"]["proceeds"]),
            "form_8949_cost_basis": currency(form_8949_totals["total"]["cost_basis"]),
            "form_8949_gain_loss": currency(form_8949_totals["total"]["gain_loss"]),
        },
        "form_8949_totals": form_8949_totals,
        "packet_includes": [
            "Excel workbook with transactions, stats, links, sales, and 8949 sheets",
            "Form 8949 short-term and long-term detail CSVs",
            "Form 8949 totals CSV and JSON",
            "Holdings reconciliation CSV",
            "Current holdings lots CSV",
            "Import warnings CSV",
            "Copied source files when still available on disk",
            "Evidence manifest, packet inventory, and SHA-256 hashes",
            "Methodology memo",
        ],
    }


def fetch_crypto_price(trans):

    symbol = f"{trans.symbol}-USD"

    start_time_obj = trans.time_stamp
    start_time_formatted = start_time_obj.isoformat(timespec='milliseconds').split('.')[0] + '.' + start_time_obj.isoformat(timespec='milliseconds').split('.')[1][:3] + 'Z'
    end_time_obj = start_time_obj + datetime.timedelta(minutes=2)
    end_time_formatted = end_time_obj.isoformat(timespec='milliseconds').split('.')[0] + '.' + end_time_obj.isoformat(timespec='milliseconds').split('.')[1][:3] + 'Z'

    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles?granularity=60&start={start_time_formatted}&end={end_time_formatted}"
    headers = {"Accept": "application/json"}
    response =  requests.request("GET", url, headers=headers, timeout=1)

    if response.status_code == 200 and len(response.json()) > 0:  # check to make sure the response from server is good
        # print(f'API Response Status Code 200 ')
        # print(response.text)
        # print(response.json())

        price = response.json()[0][4]

        # timestampnum = response.json()[0][0]
        # response_time_obj = datetime.datetime.utcfromtimestamp(timestampnum)
        # input_time_obj = dateutil.parser.parse(timestamp)

        # print(f"The Price of {symbol} was looked up using coinbase api {price} @ {start_time_obj}")
        # print(symbol)
        # print('timestamp on api input', input_time_obj)
        # print('timestamp on api response', response_time_obj)

        trans.usd_spot = price

    else:
        print()
        print("Did not receieve a valid response from Coinbase API")
        print(symbol)
        print('Type: ', trans.trans_type)
        print('Quantity: ', trans.quantity)
        print('timestamp: ', trans.time_stamp)
        print('2017-09-24T11:59:17.404Z is a valid example timestamp')
        print('Start Time: ', start_time_formatted)
        print('End Time: ', end_time_formatted)
        print(url)
        print(response)
        print('response.json(): ',response.json())


def less_than_one_cent(quantity, usd_spot):

    if quantity * usd_spot > .01:
        return False
    else:
        return True


def get_stats_table_data(transactions):
    # Stats Table Generation

    # Get links
    links = set([
            link
            for trans in transactions
            for link in trans.links
            ])

    stats_table_data = []

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
                total_purchased_usd += trans.usd_total


            elif trans.trans_type.lower() == "sell":
                total_sold_quantity += trans.quantity
                total_sold_unlinked_quantity += trans.unlinked_quantity
                total_sold_usd += trans.usd_total
                if trans.unlinked_quantity > 0:
                    profit_loss += (trans.unlinked_quantity * trans.usd_spot)

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



        stats_table_data.append({
                "symbol": f"{asset}",
                "total_purchased_quantity": format_quantity(total_purchased_quantity),
                "total_purchased_unlinked_quantity": format_quantity(total_purchased_unlinked_quantity),
                "total_purchased_usd": "${:,.2f}".format(total_purchased_usd),
                "total_sold_quantity": format_quantity(total_sold_quantity),
                "total_sold_unlinked_quantity": format_quantity(total_sold_unlinked_quantity),
                "total_sold_usd": "${:,.2f}".format(total_sold_usd),
                "total_profit_loss": "${:,.2f}".format(profit_loss),
                "total_sent_quantity": format_quantity(total_sent_quantity),
                "total_received_quantity": format_quantity(total_received_quantity),
                "holdings": format_quantity(holdings) if holdings != "N/A" else holdings

            })

    return stats_table_data


def get_all_trans_table_data(transactions):
    all_trans_table_data = []
    for trans in transactions:
        trans_data = {}
        trans_data['name'] = trans.name
        trans_data['type'] = trans.trans_type
        trans_data['asset'] = trans.symbol
        trans_data['time_stamp'] = trans.time_stamp
        trans_data['usd_spot'] = "${:,.2f}".format(trans.usd_spot)
        trans_data['quantity'] = trans.quantity
        trans_data['unlinked_quantity'] = trans.unlinked_quantity
        trans_data['usd_total'] = "${:,.2f}".format(trans.usd_total)

        all_trans_table_data.append(trans_data)

    return all_trans_table_data


def td_format(td_object):
    # Used to Format Link Time Deltas
    seconds = int(td_object.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings=[]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value , seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)




def get_linked_table_data(transactions, asset, date_range):


    if date_range:

        start_date = date_range['start_date']
        end_date = date_range['end_date']


    # Filter Transactions to date range
    filtered_transactions = []

    for trans in transactions:
        if asset:
            if trans.symbol != asset:
                continue

        # Ensure all datetime objects are offset-naive for comparison
        start_date = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
        end_date = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
        trans_time_stamp = trans.time_stamp.replace(tzinfo=None) if trans.time_stamp.tzinfo else trans.time_stamp

        if start_date and not end_date:
            if trans_time_stamp >= start_date:
                filtered_transactions.append(trans)

        elif not start_date and end_date:
            if trans_time_stamp <= end_date:
                filtered_transactions.append(trans)

        elif start_date and end_date:
            if trans_time_stamp >= start_date and trans_time_stamp <= end_date:
                filtered_transactions.append(trans)

    # Get links
    links = set([
            link
            for trans in filtered_transactions
            for link in trans.links
            ])

    # print(f" {asset} len of links {len(links)}")

    # Get linked Table Data
    linked_table_data = []
    for link in links:
        cost_basis = link.cost_basis + (link.buy.fee if link.buy.fee is not None else 0)
        linked_table_data.append([
            link.quantity,
            "${:,.2f}".format(link.profit_loss),
            td_format(link.holding_duration),
            link.buy.time_stamp,
            link.buy.quantity,
            "${:,.2f}".format(link.buy.usd_total),
            link.sell.time_stamp,
            link.sell.quantity,
            "${:,.2f}".format(link.sell.usd_total),
        ])

    return linked_table_data


def get_linkable_table_data(transactions, trans1_obj):
    # Get Linkable Table Data
    linkable_table_data = []
    for trans in transactions:

        # Don't show if different Asset types
        if trans1_obj.symbol != trans.symbol:
            continue

        # Don't show if 0.0 unlinked quantity WE SHOULD TEST 0 NOT 0.0 AS 0.01 ISSUE CAN ARRISE
        if trans1_obj.unlinked_quantity <= 0.0 or trans.unlinked_quantity <= 0.0:
            continue

        # Don't show if same type
        if trans.trans_type == trans1_obj.trans_type:
            continue

        # Don't show if already linked
        # if trans.name in other_transactions:
        #     continue

        # Don't show if time problem
        if trans1_obj.trans_type == "sell":
            if trans1_obj.time_stamp < trans.time_stamp:
                continue

        elif trans1_obj.trans_type == "buy":
            if trans1_obj.time_stamp < trans.time_stamp:
                continue

        # Determine Buy and Sell Objects
        if trans1_obj.trans_type == "sell" and trans.trans_type == "buy":

            sell_obj = trans1_obj
            buy_obj = trans

        elif trans1_obj.trans_type == "buy" and trans.trans_type == "sell":
            sell_obj = trans
            buy_obj = trans1_obj

        else:
            continue

        # Determine max link quantity
        if sell_obj.unlinked_quantity <= buy_obj.unlinked_quantity:
            quantity = sell_obj.unlinked_quantity

        elif sell_obj.unlinked_quantity >= buy_obj.unlinked_quantity:
            quantity = buy_obj.unlinked_quantity

        # Determine link profitability
        buy_price = quantity * buy_obj.usd_spot
        sell_price = quantity * sell_obj.usd_spot
        profit = sell_price - buy_price


        linkable_table_data.append([
            trans.name,
            trans.trans_type.capitalize(),
            trans.symbol,
            trans.time_stamp,
            trans.quantity,
            trans.unlinked_quantity,
            "${:,.2f}".format(trans.usd_spot),
            "${:,.2f}".format(trans.usd_total),
            "${:,.2f}".format(profit)
            ])

    return linkable_table_data


def get_stats_table_data_range(transactions, date_range=None):
    # Stats Table Generation with date range

    if date_range:

        start_date = date_range['start_date']
        end_date = date_range['end_date']

        # Ensure start_date and end_date are offset-naive
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)

        # Filter Transactions to date range
        filtered_transactions = []
        for trans in transactions:
            trans_time_stamp = trans.time_stamp
            # Ensure trans_time_stamp is offset-naive
            if trans_time_stamp.tzinfo is not None:
                trans_time_stamp = trans_time_stamp.replace(tzinfo=None)

            if start_date and not end_date:
                if trans_time_stamp >= start_date:
                    filtered_transactions.append(trans)

            elif not start_date and end_date:
                if trans_time_stamp <= end_date:
                    filtered_transactions.append(trans)

            elif start_date and end_date:
                if trans_time_stamp >= start_date and trans_time_stamp <= end_date:
                    filtered_transactions.append(trans)


        # Get links
        links = set([
                link
                for trans in filtered_transactions
                for link in trans.links
                ])


        stats_table_data = []

        for asset in transactions.assets:

            total_purchased_quantity = 0.0
            total_purchased_unlinked_quantity = 0.0
            total_purchased_usd = 0.0

            total_sold_quantity = 0.0
            total_sold_unlinked_quantity = 0.0
            total_sold_usd = 0.0

            total_sent_quantity = 0.0
            total_received_quantity = 0.0

            profit_loss_total = 0.0
            profit_loss_short = 0.0
            profit_loss_long = 0.0

            proceeds_long = 0.0
            cost_basis_long = 0.0
            gain_long = 0.0

            proceeds_short = 0.0
            cost_basis_short = 0.0
            gain_short = 0.0


            buy_prices = []
            sell_prices = []

            # average_holdings_length = 0.0

            num_buys = 0
            num_sells = 0
            num_sends = 0
            num_receives = 0

            num_links = 0


            for row in get_form_8949_report_rows(transactions, asset=asset, date_range=date_range):
                num_links += 1
                profit_loss_total += row["gain_loss"]
                if row["term"] == "long":
                    profit_loss_long += row["gain_loss"]
                    proceeds_long += row["proceeds"]
                    cost_basis_long += row["cost_basis"]
                    gain_long += row["gain_loss"]
                else:
                    profit_loss_short += row["gain_loss"]
                    proceeds_short += row["proceeds"]
                    cost_basis_short += row["cost_basis"]
                    gain_short += row["gain_loss"]


            for trans in filtered_transactions:
                if trans.symbol == asset:

                    if trans.trans_type.lower() == "buy":
                        num_buys += 1
                        total_purchased_quantity += trans.quantity
                        if trans.unlinked_quantity < 0:
                            print(f"Unlinked Quantity is negative for {asset} {trans.symbol} {trans.trans_type} {trans.name} UNLINKED {trans.unlinked_quantity}")
                        total_purchased_unlinked_quantity += trans.unlinked_quantity
                        total_purchased_usd += trans.usd_total
                        buy_prices.append(trans.usd_total)


                    elif trans.trans_type.lower() == "sell":
                        num_sells += 1
                        total_sold_quantity += trans.quantity
                        if trans.unlinked_quantity < 0:
                            print(f"Unlinked Quantity is negative for {asset} {trans.symbol} {trans.trans_type} {trans.name} UNLINKED {trans.unlinked_quantity}")
                        total_sold_unlinked_quantity += trans.unlinked_quantity
                        total_sold_usd += trans.usd_total

                        # Not sure why this is here, probably for a good reason?? what to do with unlinked?
                        # if trans.unlinked_quantity > 0:
                            # profit_loss += (trans.usd_spot * trans.unlinked_quantity)

                        sell_prices.append(trans.usd_total)

                    elif trans.trans_type.lower() == "send":
                        num_sends += 1
                        total_sent_quantity += trans.quantity

                    elif trans.trans_type.lower() == "receive":
                        num_receives += 1
                        total_received_quantity += trans.quantity

            if len(buy_prices) > 0 and total_purchased_quantity:
                average_buy_price = total_purchased_usd / total_purchased_quantity

            else:
                average_buy_price = 0.0

            if len(sell_prices) > 0 and total_sold_quantity:
                average_sell_price = total_sold_usd / total_sold_quantity

            else:
                average_sell_price = 0.0

            holdings = "N/A"

            for a in transactions.asset_objects:
                if a.symbol != asset:
                    continue

                # print(f"Asset Object symbol {a.symbol} Asset {asset} Holdings {a.holdings}")
                if a.holdings is not None:
                    holdings = a.holdings
                    # print(f"Asset Object symbol {a.symbol} Asset {asset} Holdings {a.holdings}")

            total_sold_unlinked_quantity = round_decimals_down(total_sold_unlinked_quantity)
            if total_sold_unlinked_quantity != 0 and abs(total_sold_unlinked_quantity) < .0009:
                total_sold_unlinked_quantity = "Less than .0009"


            stats_table_data.append({
                    "symbol": f"{asset}",
                    "total_purchased_quantity": format_quantity(total_purchased_quantity),
                    "total_purchased_unlinked_quantity": format_quantity(round_decimals_down(total_purchased_unlinked_quantity)),
                    "total_purchased_usd": "${:,.2f}".format(total_purchased_usd),

                    "total_sold_quantity": format_quantity(total_sold_quantity),
                    "total_sold_unlinked_quantity": format_quantity(total_sold_unlinked_quantity),
                    "total_sold_usd": "${:,.2f}".format(total_sold_usd),
                    "profit_loss_total": "${:,.2f}".format(profit_loss_total),
                    "profit_loss_short": "${:,.2f}".format(profit_loss_short),
                    "profit_loss_long": "${:,.2f}".format(profit_loss_long),

                    "proceeds_long": "${:,.2f}".format(proceeds_long),
                    "cost_basis_long": "${:,.2f}".format(cost_basis_long),
                    "gain_long": "${:,.2f}".format(gain_long),

                    "proceeds_short": "${:,.2f}".format(proceeds_short),
                    "cost_basis_short": "${:,.2f}".format(cost_basis_short),
                    "gain_short": "${:,.2f}".format(gain_short),

                    "total_sent_quantity": format_quantity(total_sent_quantity),
                    "total_received_quantity": format_quantity(total_received_quantity),

                    "num_buys": num_buys,
                    "num_sells": num_sells,

                    "num_links": num_links,

                    "average_buy_price": "${:,.2f}".format(average_buy_price),
                    "average_sell_price": "${:,.2f}".format(average_sell_price),
                    "holdings": format_quantity(holdings) if holdings != "N/A" else holdings,
                    "has_sells_without_links": num_sells > 0 and num_links == 0,
                    "has_unlinked_sells": total_sold_unlinked_quantity != 0,

                })


    return stats_table_data

def get_current_holdings_lots(transactions, asset=None):
    declared_holdings = transactions.get_holdings(asset) if asset and hasattr(transactions, "get_holdings") else None
    allocation_remaining = declared_holdings
    lots = []

    for trans in transactions:
        if asset and trans.symbol != asset:
            continue

        if trans.symbol not in transactions.assets:
            continue

        if trans.trans_type not in ("buy", "receive"):
            continue

        remaining_quantity = trans.unlinked_quantity
        if remaining_quantity <= 0.000000001:
            continue

        lots.append((trans, remaining_quantity))

    if declared_holdings is not None:
        lots.sort(key=lambda lot: comparable_datetime(lot[0].time_stamp), reverse=True)
    else:
        lots.sort(key=lambda lot: comparable_datetime(lot[0].time_stamp))

    table_data = []
    for trans, remaining_quantity in lots:
        estimated_held_quantity = remaining_quantity
        if allocation_remaining is not None:
            if allocation_remaining <= 0.000000001:
                continue

            estimated_held_quantity = min(remaining_quantity, allocation_remaining)
            allocation_remaining -= estimated_held_quantity

        cost_basis = estimated_held_quantity * trans.usd_spot
        original_cost = trans.quantity * trans.usd_spot

        table_data.append({
            "asset": trans.symbol,
            "type": trans.trans_type,
            "acquired_at": trans.time_stamp,
            "estimated_held_quantity": estimated_held_quantity,
            "original_quantity": trans.quantity,
            "usd_spot": trans.usd_spot,
            "estimated_basis": cost_basis,
            "original_basis": original_cost,
            "source": trans.source,
        })

    table_data.sort(key=lambda row: (row["asset"], comparable_datetime(row["acquired_at"])))
    return table_data


def get_current_holdings_lot_table_data(transactions, asset=None):
    table_data = []
    for lot in get_current_holdings_lots(transactions, asset):
        acquired_at = lot["acquired_at"]
        if hasattr(acquired_at, "strftime"):
            acquired_at = datetime.datetime.strftime(acquired_at, "%Y-%m-%d %H:%M:%S")

        table_data.append([
            lot["asset"],
            lot["type"].capitalize(),
            acquired_at,
            format_quantity(lot["estimated_held_quantity"]),
            format_quantity(lot["original_quantity"]),
            "${:,.2f}".format(lot["usd_spot"]),
            "${:,.2f}".format(lot["estimated_basis"]),
            "${:,.2f}".format(lot["original_basis"]),
            lot["source"],
        ])

    return table_data


def get_default_asset_spot(transactions, asset):
    latest_transaction = None

    for trans in transactions:
        if trans.symbol != asset or trans.usd_spot <= 0:
            continue

        if (
            latest_transaction is None
            or comparable_datetime(trans.time_stamp) > comparable_datetime(latest_transaction.time_stamp)
        ):
            latest_transaction = trans

    return latest_transaction.usd_spot if latest_transaction else 0.0


def get_unrealized_chart_data(transactions, asset, current_usd_spot=None):
    current_spot = parse_float_value(current_usd_spot)
    if current_spot is None or current_spot <= 0:
        current_spot = get_default_asset_spot(transactions, asset)

    chart_points = []
    if current_spot <= 0:
        return {
            "current_usd_spot": current_spot,
            "points": chart_points,
        }

    for lot in get_current_holdings_lots(transactions, asset):
        quantity = lot["estimated_held_quantity"]
        current_value = quantity * current_spot
        cost_basis = lot["estimated_basis"]
        gain_loss = current_value - cost_basis
        acquired_at = lot["acquired_at"]
        if hasattr(acquired_at, "strftime"):
            acquired_at = datetime.datetime.strftime(acquired_at, "%Y-%m-%d %H:%M:%S")

        chart_points.append({
            "x": acquired_at,
            "y": round(gain_loss, 2),
            "quantity": format_quantity(quantity),
            "usd_spot": "${:,.2f}".format(current_spot),
            "cost_basis": "${:,.2f}".format(cost_basis),
            "current_value": "${:,.2f}".format(current_value),
            "gain_loss": "${:,.2f}".format(gain_loss),
        })

    return {
        "current_usd_spot": current_spot,
        "points": chart_points,
    }


def get_holdings_reconciliation(transactions, asset):
    declared_holdings = transactions.get_holdings(asset) if hasattr(transactions, "get_holdings") else None
    totals = {
        "buy": 0.0,
        "sell": 0.0,
        "send": 0.0,
        "receive": 0.0,
    }

    for trans in transactions:
        if trans.symbol == asset and trans.trans_type in totals:
            totals[trans.trans_type] += trans.quantity

    expected_holdings = totals["buy"] - totals["sell"]
    imported_net = totals["buy"] + totals["receive"] - totals["sell"] - totals["send"]
    lot_quantity = 0.0

    for trans in transactions:
        if trans.symbol == asset and trans.trans_type in ("buy", "receive"):
            lot_quantity += max(trans.unlinked_quantity, 0.0)

    if declared_holdings is None:
        difference = None
        status = "Needs declared holdings"
        next_action = "Enter the actual current holding for this asset."
        allocation_method = "Showing unlinked buy/receive lots because no declared holdings are saved."
    else:
        difference = expected_holdings - declared_holdings
        allocation_method = "FIFO remaining estimate: oldest disposals are assumed consumed first, so declared holdings are allocated to newest available lots."

        if abs(difference) <= 0.00000001:
            status = "Matched"
            next_action = "Review lots and proceed to basis linking."
        elif difference > 0:
            status = "Mismatch"
            next_action = "Classify missing disposals/losses or convert sends to sells until the difference is resolved."
        else:
            status = "Mismatch"
            next_action = "Add missing acquisitions or convert receives to buys until the difference is resolved."

    return {
        "asset": asset,
        "declared_holdings": declared_holdings,
        "buy_quantity": totals["buy"],
        "sell_quantity": totals["sell"],
        "expected_holdings": expected_holdings,
        "imported_net": imported_net,
        "available_lot_quantity": lot_quantity,
        "difference": difference,
        "status": status,
        "next_action": next_action,
        "lot_allocation_method": allocation_method,
    }


def get_holdings_reconciliation_summary(transactions, asset):
    reconciliation = get_holdings_reconciliation(transactions, asset)

    return [
        [
            "Declared Holdings",
            format_quantity(reconciliation["declared_holdings"])
            if reconciliation["declared_holdings"] is not None
            else "N/A",
        ],
        ["Buy Quantity", format_quantity(reconciliation["buy_quantity"])],
        ["Sell Quantity", format_quantity(reconciliation["sell_quantity"])],
        ["Expected From Buys/Sells Only", format_quantity(reconciliation["expected_holdings"])],
        ["Imported Net After Transfers", format_quantity(reconciliation["imported_net"])],
        ["Available Buy/Receive Lot Quantity", format_quantity(reconciliation["available_lot_quantity"])],
        [
            "Difference vs Declared Holdings",
            format_quantity(reconciliation["difference"])
            if reconciliation["difference"] is not None
            else "N/A",
        ],
        ["Status", reconciliation["status"]],
        ["Next Action", reconciliation["next_action"]],
        ["Lot Allocation Method", reconciliation["lot_allocation_method"]],
    ]


def get_multi_asset_holdings_reconciliation_table_data(transactions):
    assets = set(getattr(transactions, "assets", set()))
    assets.update(
        asset_object.symbol
        for asset_object in getattr(transactions, "asset_objects", [])
        if getattr(asset_object, "symbol", None)
    )
    assets = sorted(asset for asset in assets if asset not in FIAT_ASSET_SYMBOLS)

    table_data = []
    for asset in assets:
        reconciliation = get_holdings_reconciliation(transactions, asset)
        table_data.append([
            asset,
            (
                format_quantity(reconciliation["declared_holdings"])
                if reconciliation["declared_holdings"] is not None
                else "N/A"
            ),
            format_quantity(reconciliation["expected_holdings"]),
            format_quantity(reconciliation["imported_net"]),
            format_quantity(reconciliation["available_lot_quantity"]),
            (
                format_quantity(reconciliation["difference"])
                if reconciliation["difference"] is not None
                else "N/A"
            ),
            reconciliation["status"],
            reconciliation["next_action"],
        ])

    return table_data


def get_all_trans_table_data_range(transactions, asset, date_range):

    if date_range:

        start_date = date_range['start_date']
        end_date = date_range['end_date']

        # Filter Transactions to date range
        filtered_transactions = []
        for trans in transactions:
            if start_date and not end_date:
                if trans.time_stamp >= start_date:
                    filtered_transactions.append(trans)

            elif not start_date and end_date:
                if trans.time_stamp <= end_date:
                    filtered_transactions.append(trans)

            elif start_date and end_date:
                if trans.time_stamp >= start_date and trans.time_stamp <= end_date:
                    filtered_transactions.append(trans)


    all_trans_table_data = []
    for trans in filtered_transactions:

        all_trans_table_data.append([
            trans.name,
            trans.trans_type,
            trans.symbol,
            trans.time_stamp,
            trans.quantity,
            "${:,.2f}".format(trans.usd_spot),
            "${:,.2f}".format(trans.usd_total)
        ])


    return all_trans_table_data


def get_transactions_date_range(transactions, date_range):

    if date_range['start_date'] == '':
        first_time_stamps = transactions.first_transaction_date()

        first_time_stamp = None
        for time_stamp in first_time_stamps.values():
            if first_time_stamp is None:
                first_time_stamp = time_stamp

            if time_stamp < first_time_stamp:
                first_time_stamp = time_stamp

        date_range['start_date'] = first_time_stamp

    else:
        date_range['start_date'] = datetime.datetime.strptime(date_range['start_date'], "%m/%d/%Y %H:%M %p")


    if date_range['end_date'] == '':
        last_time_stamps = transactions.last_transaction_date()

        last_time_stamp = None
        for time_stamp in last_time_stamps.values():
            if last_time_stamp is None:
                last_time_stamp = time_stamp
                continue

            if time_stamp > last_time_stamp:
                last_time_stamp = time_stamp

        date_range['end_date'] = last_time_stamp

    else:
        date_range['end_date'] = datetime.datetime.strptime(date_range['end_date'], "%m/%d/%Y %H:%M %p")

    return date_range



def get_sells_trans_table_data_range(transactions, asset, date_range):

    if date_range:

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


    table_data = []
    for trans in filtered_transactions:
        if trans.trans_type == "sell":

            trans.update_linked_transactions()

            if trans.unlinked_quantity != 0.0 and trans.unlinked_quantity < 0.0009:

                unlinked_quantity = "Less than 0.0009"
            else:
                unlinked_quantity = trans.unlinked_quantity

            table_data.append([
                trans.source,
                trans.symbol,
                datetime.datetime.strftime(trans.time_stamp, "%Y-%m-%d %H:%M:%S.%f"),
                trans.quantity,
                unlinked_quantity,
                "${:,.2f}".format(trans.usd_spot),
                "${:,.2f}".format(trans.usd_total)
            ])



    return table_data


def get_buys_trans_table_data_range(transactions, asset, date_range):

    if date_range:

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


    table_data = []
    for trans in filtered_transactions:
        if trans.trans_type == "buy":

            if trans.unlinked_quantity != 0.0 and trans.unlinked_quantity < 0.0009:

                unlinked_quantity = "Less than 0.0009"
            else:
                unlinked_quantity = trans.unlinked_quantity

            table_data.append([
                trans.source,
                trans.symbol,
                datetime.datetime.strftime(trans.time_stamp, "%Y-%m-%d %H:%M:%S"),
                trans.quantity,
                unlinked_quantity,
                "${:,.2f}".format(trans.usd_spot),
                "${:,.2f}".format(trans.usd_total)
            ])



    return table_data


def get_sends_trans_table_data_range(transactions, asset, date_range):

    if date_range:

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


    table_data = []
    for trans in filtered_transactions:
        if trans.trans_type == "send":

            if trans.unlinked_quantity != 0.0 and trans.unlinked_quantity < 0.0009:

                unlinked_quantity = "Less than 0.0009"
            else:
                unlinked_quantity = trans.unlinked_quantity


            table_data.append([
                trans.source,
                trans.symbol,
                datetime.datetime.strftime(trans.time_stamp, "%Y-%m-%d %H:%M:%S"),
                trans.quantity,
                unlinked_quantity,
                "${:,.2f}".format(trans.usd_spot),
                "${:,.2f}".format(trans.usd_total)
            ])



    return table_data



def get_receives_trans_table_data_range(transactions, asset, date_range):

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


    table_data = []
    for trans in filtered_transactions:
        if trans.trans_type == "receive":


            if trans.unlinked_quantity != 0.0 and trans.unlinked_quantity < 0.0009:

                unlinked_quantity = "Less than 0.0009"
            else:
                unlinked_quantity = trans.unlinked_quantity

            table_data.append([
                trans.source,
                trans.symbol,
                datetime.datetime.strftime(trans.time_stamp, "%Y-%m-%d %H:%M:%S"),
                trans.quantity,
                unlinked_quantity,
                "${:,.2f}".format(trans.usd_spot),
                "${:,.2f}".format(trans.usd_total)
            ])



    return table_data


def get_trans_obj_from_table_data(transactions, symbol, trans_type, quantity, time_stamp) -> Transaction:

    trans_obj = None

    for trans in transactions:

        if trans.symbol == symbol and trans.trans_type == trans_type and trans.quantity == quantity:

            if isinstance(trans.time_stamp, datetime.date):
                trans2_time_stamp = trans.time_stamp
                # trans2_time_stamp = trans2_time_stamp.replace(microsecond=0)

            else:
                trans2_time_stamp = trans.time_stamp.to_pydatetime()
                time_stamp = parser.parse(time_stamp, tzinfos=tzinfos)
                trans2_time_stamp = trans2_time_stamp.replace(tzinfo=tzutc())
                # trans2_time_stamp = trans2_time_stamp.replace(microsecond=0)


            print(time_stamp, trans2_time_stamp)
            if time_stamp == trans2_time_stamp:

                # print(f"Trans with Symbol {sell_symbol} and quantity {sell_quantity} Found")
                # print(f"USD Spot {sell_usd_spot}  {trans.usd_spot}")
                # print(f"\nTrans 1 Time Stamp {sell_time_stamp} ")
                # print(f"Time Stamp {sell_time_stamp}  {trans2_time_stamp}")
                # print(f"Time Stamp {type(sell_time_stamp)}  {type(trans2_time_stamp)}")
                # print(sell_time_stamp == trans2_time_stamp)

                trans_obj = trans

                break


    return trans_obj


def get_all_links_table_data(transactions, asset):


    # Get links
    links = set([
            link
            for trans in transactions if trans.symbol == asset
            for link in trans.links
            ])


    table_data = []

    for link in links:

        table_data.append([
            link.symbol,
            datetime.datetime.strftime(link.buy.time_stamp, "%Y-%m-%d %H:%M:%S"),
            datetime.datetime.strftime(link.sell.time_stamp, "%Y-%m-%d %H:%M:%S"),
            "${:,.2f}".format(link.buy.usd_spot),
            "${:,.2f}".format(link.sell.usd_spot),
            link.quantity,
            "${:,.2f}".format(link.proceeds),
            "${:,.2f}".format(link.cost_basis),
            "${:,.2f}".format(link.profit_loss)
        ])



    return table_data


def round_decimals_down(number:float, decimals:int=8):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    quantizer = Decimal("1").scaleb(-decimals)
    return float(Decimal(str(number)).quantize(quantizer, rounding=ROUND_FLOOR))

# This module will handle general utility functions.

# Add utility functions here, e.g., for rounding decimals or handling time zones.


