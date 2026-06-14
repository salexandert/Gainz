import datetime
from transaction import Transaction
from dateutil.tz import tzutc
import requests
import datetime
import os
import math
from decimal import Decimal, ROUND_FLOOR
from date_parsing import GAINZ_TZINFOS, parse_gainz_datetime

os.environ['REQUESTS_CA_BUNDLE'] = "certifi/cacert.pem"

# Define the timezone information
tzinfos = GAINZ_TZINFOS

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


def _import_warning_review_rows(warnings, transactions=None):
    from app.services.import_warning_service import import_warning_review_rows

    return import_warning_review_rows(warnings, transactions=transactions)


def _unresolved_import_warning_rows(transactions):
    from app.services.import_warning_service import unresolved_import_warning_rows

    return unresolved_import_warning_rows(transactions)


def _source_overlap_rows(transactions):
    from app.services.source_overlap_service import detect_source_overlaps

    return detect_source_overlaps(transactions)


def _tax_evidence_inventory_summary(transactions, tax_alignment=None):
    from app.services.tax_evidence_service import get_tax_evidence_inventory_summary

    return get_tax_evidence_inventory_summary(transactions, alignment=tax_alignment)


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


def get_form_8949_totals_by_year(transactions):
    totals_by_year = {}

    for row in get_form_8949_report_rows(transactions):
        year = int(row["year"])
        if year not in totals_by_year:
            totals_by_year[year] = {
                "short": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
                "long": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
                "total": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
            }

        for bucket in (row["term"], "total"):
            totals_by_year[year][bucket]["rows"] += 1
            totals_by_year[year][bucket]["proceeds"] += row["proceeds"]
            totals_by_year[year][bucket]["cost_basis"] += row["cost_basis"]
            totals_by_year[year][bucket]["gain_loss"] += row["gain_loss"]

    return totals_by_year


def _empty_form_8949_totals():
    return {
        "short": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
        "long": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
        "total": {"rows": 0, "proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
    }


def _tax_years_to_review(transactions, totals_by_year):
    years = set(totals_by_year.keys())

    for record in getattr(transactions, "tax_year_records", []) or []:
        year = record.get("year")
        if year is not None:
            years.add(int(year))

    for transaction in getattr(transactions, "transactions", []) or []:
        if getattr(transaction, "trans_type", "") == "sell" and hasattr(transaction.time_stamp, "year"):
            years.add(int(transaction.time_stamp.year))

    return sorted(years, reverse=True)


def _year_sell_review_counts(transactions, year):
    sell_count = 0
    unlinked_sell_count = 0
    unlinked_quantity = 0.0

    for transaction in getattr(transactions, "transactions", []) or []:
        if getattr(transaction, "trans_type", "") != "sell":
            continue
        if not hasattr(transaction.time_stamp, "year") or int(transaction.time_stamp.year) != int(year):
            continue

        sell_count += 1
        if getattr(transaction, "unlinked_quantity", 0) > 0.000000009:
            unlinked_sell_count += 1
            unlinked_quantity += transaction.unlinked_quantity

    return {
        "sell_count": sell_count,
        "unlinked_sell_count": unlinked_sell_count,
        "unlinked_quantity": unlinked_quantity,
    }


def _money_difference(calculated, reported):
    if reported is None:
        return None

    return round(float(calculated) - float(reported), 2)


def _tax_alignment_status(record, differences, sell_counts, tolerance):
    if record is None:
        return {
            "status": "Needs filed totals",
            "status_class": "status-needs-declared-holdings",
            "next_action": "Enter the totals reported for this year and record the payment reference or filing note.",
        }

    if sell_counts["unlinked_sell_count"] > 0:
        return {
            "status": "Needs basis review",
            "status_class": "status-unlinked-sales",
            "next_action": "Review or create basis links for sells in this year before relying on the comparison.",
        }

    mismatched_fields = [
        label
        for label, value in differences.items()
        if value is not None and abs(value) > tolerance
    ]
    if mismatched_fields:
        return {
            "status": "Needs review",
            "status_class": "status-needs-review",
            "next_action": "Compare Gainz totals with the filed return for: " + ", ".join(mismatched_fields) + ".",
        }

    if record.get("tax_paid") is None:
        return {
            "status": "Needs payment record",
            "status_class": "status-unlinked-sales",
            "next_action": "Record the tax paid amount or explain why no separate crypto payment was due.",
        }

    return {
        "status": "Aligned",
        "status_class": "status-verified",
        "next_action": "Totals are within the comparison tolerance. Keep source records and filing/payment evidence with the audit packet.",
    }


def _display_money_or_blank(value):
    if value is None:
        return ""

    return currency(value)


def get_tax_filing_alignment_summary(transactions, tolerance=1.0):
    totals_by_year = get_form_8949_totals_by_year(transactions)
    records_by_year = {
        int(record["year"]): record
        for record in getattr(transactions, "tax_year_records", []) or []
        if record.get("year") is not None
    }

    rows = []
    for year in _tax_years_to_review(transactions, totals_by_year):
        totals = totals_by_year.get(year, _empty_form_8949_totals())
        calculated = totals["total"]
        record = records_by_year.get(year)
        sell_counts = _year_sell_review_counts(transactions, year)
        differences = {
            "proceeds": _money_difference(calculated["proceeds"], record.get("reported_proceeds") if record else None),
            "cost basis": _money_difference(calculated["cost_basis"], record.get("reported_cost_basis") if record else None),
            "gain/loss": _money_difference(calculated["gain_loss"], record.get("reported_gain_loss") if record else None),
        }
        status = _tax_alignment_status(record, differences, sell_counts, tolerance)

        rows.append({
            "year": year,
            "status": status["status"],
            "status_class": status["status_class"],
            "next_action": status["next_action"],
            "calculated_rows": calculated["rows"],
            "sell_count": sell_counts["sell_count"],
            "unlinked_sell_count": sell_counts["unlinked_sell_count"],
            "unlinked_quantity": format_quantity(sell_counts["unlinked_quantity"]),
            "calculated_proceeds": calculated["proceeds"],
            "calculated_cost_basis": calculated["cost_basis"],
            "calculated_gain_loss": calculated["gain_loss"],
            "reported_proceeds": record.get("reported_proceeds") if record else None,
            "reported_cost_basis": record.get("reported_cost_basis") if record else None,
            "reported_gain_loss": record.get("reported_gain_loss") if record else None,
            "tax_paid": record.get("tax_paid") if record else None,
            "filing_status": record.get("filing_status", "") if record else "",
            "evidence_reference": record.get("evidence_reference", "") if record else "",
            "notes": record.get("notes", "") if record else "",
            "updated_at": record.get("updated_at", "") if record else "",
            "difference_proceeds": differences["proceeds"],
            "difference_cost_basis": differences["cost basis"],
            "difference_gain_loss": differences["gain/loss"],
            "calculated_proceeds_display": currency(calculated["proceeds"]),
            "calculated_cost_basis_display": currency(calculated["cost_basis"]),
            "calculated_gain_loss_display": currency(calculated["gain_loss"]),
            "reported_proceeds_display": _display_money_or_blank(record.get("reported_proceeds") if record else None),
            "reported_cost_basis_display": _display_money_or_blank(record.get("reported_cost_basis") if record else None),
            "reported_gain_loss_display": _display_money_or_blank(record.get("reported_gain_loss") if record else None),
            "tax_paid_display": _display_money_or_blank(record.get("tax_paid") if record else None),
            "difference_proceeds_display": _display_money_or_blank(differences["proceeds"]),
            "difference_cost_basis_display": _display_money_or_blank(differences["cost basis"]),
            "difference_gain_loss_display": _display_money_or_blank(differences["gain/loss"]),
            "has_record": record is not None,
            "payment_recorded": bool(record and record.get("tax_paid") is not None),
        })

    status_counts = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    if not rows:
        overall_status = "No years to review"
        overall_status_class = "status-verified"
        next_action = "Import and link sell activity, then record filed totals for each year you want to compare."
    elif all(row["status"] == "Aligned" for row in rows):
        overall_status = "Aligned"
        overall_status_class = "status-verified"
        next_action = "Generate an audit packet and keep official filing/payment records with it."
    else:
        overall_status = "Needs review"
        overall_status_class = "status-needs-review"
        next_action = next(row["next_action"] for row in rows if row["status"] != "Aligned")

    return {
        "overall_status": overall_status,
        "overall_status_class": overall_status_class,
        "next_action": next_action,
        "tolerance": tolerance,
        "rows": rows,
        "status_counts": status_counts,
        "metrics": {
            "years": len(rows),
            "aligned_years": status_counts.get("Aligned", 0),
            "years_needing_review": len([row for row in rows if row["status"] != "Aligned"]),
            "declared_years": len([row for row in rows if row["has_record"]]),
            "payment_records": len([row for row in rows if row["payment_recorded"]]),
        },
    }


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


def _basis_review_note(transactions, asset):
    if hasattr(transactions, "get_basis_review_note"):
        return transactions.get_basis_review_note(asset)

    return None


def _basis_review_needs_research(transactions, asset):
    note = _basis_review_note(transactions, asset)
    return bool(note and note.get("status") == "needs_research")


def _basis_review_note_text(transactions, asset):
    note = _basis_review_note(transactions, asset)
    return (note or {}).get("note", "")


def get_missing_basis_review_rows(transactions):
    rows = []

    for transaction in sorted(
        getattr(transactions, "transactions", []) or [],
        key=lambda item: (
            comparable_datetime(getattr(item, "time_stamp", "")),
            getattr(item, "symbol", ""),
        ),
    ):
        if getattr(transaction, "trans_type", "") != "sell":
            continue

        unlinked_quantity = getattr(transaction, "unlinked_quantity", 0)
        if unlinked_quantity <= 0.000000009:
            continue

        asset = transaction.symbol
        needs_research = _basis_review_needs_research(transactions, asset)
        note_text = _basis_review_note_text(transactions, asset)
        rows.append({
            "asset": asset,
            "date": _format_report_datetime(transaction.time_stamp),
            "quantity": format_quantity(transaction.quantity),
            "unlinked_quantity": format_quantity(unlinked_quantity),
            "source": os.path.basename(str(getattr(transaction, "source", "") or "")) or "Unknown source",
            "status": "Needs user research" if needs_research else "Missing acquisition basis",
            "note": note_text,
            "message": (
                f"{asset} sale on {_format_report_datetime(transaction.time_stamp)} needs "
                f"{format_quantity(unlinked_quantity)} {asset} of earlier acquisition basis before generated reports are filing-ready."
            ),
        })

    return rows


def _missing_current_holdings_records(holdings_rows):
    return [
        {
            "asset": row[0],
            "message": f"Current holdings are not entered for {row[0]}.",
        }
        for row in holdings_rows
        if row[6] == "Needs declared holdings"
    ]


def _missing_holdings_explanation_records(holdings_rows):
    records = []
    for row in holdings_rows:
        if row[6] != "Needs Review":
            continue

        records.append({
            "asset": row[0],
            "message": (
                f"Declared {row[0]} is {row[1]}, but imported buy/sell net is {row[2]}. "
                "Gainz needs transfers, disposals, losses, or missing source files to explain the difference."
            ),
        })

    return records


def _missing_filed_total_records(tax_alignment, tax_evidence_inventory=None):
    if tax_evidence_inventory is not None:
        return [
            {
                "year": row["year"],
                "status": row["status"],
                "status_class": row["status_class"],
                "message": row["next_action"],
                "what_gainz_found": row["what_gainz_found"],
                "what_gainz_needs": row["what_gainz_needs"],
            }
            for row in tax_evidence_inventory["review_rows"]
        ]

    return [
        {
            "year": row["year"],
            "status": row["status"],
            "message": (
                f"Filed totals not recorded for {row['year']}. If you have Crypto Taxes Paid.csv, "
                "record those totals in Tax Filing Review instead of importing it as transaction activity."
                if row["status"] == "Needs filed totals"
                else row["next_action"]
            ),
        }
        for row in tax_alignment["rows"]
        if row["status"] != "Aligned"
    ]


def _reconciliation_checklist(
    transactions,
    holdings_rows,
    missing_basis_rows,
    unresolved_warning_rows,
    source_overlap_rows,
    tax_alignment,
    tax_evidence_inventory,
    draft_acknowledged=False,
):
    current_holdings_entered = not any(row[6] == "Needs declared holdings" for row in holdings_rows)
    fifo_run = len(missing_basis_rows) == 0
    import_warnings_reviewed = len(unresolved_warning_rows) == 0
    source_overlaps_reviewed = len(source_overlap_rows) == 0
    missing_basis_reviewed = len(missing_basis_rows) == 0
    tax_evidence_reviewed = tax_evidence_inventory["metrics"]["years_needing_review"] == 0

    return [
        {
            "label": "Current holdings entered",
            "complete": current_holdings_entered,
            "detail": "All assets have declared current holdings." if current_holdings_entered else "Enter holdings for every asset, or use the bulk holdings step.",
        },
        {
            "label": "FIFO run",
            "complete": fifo_run,
            "detail": "No unlinked sales remain." if fifo_run else "Run FIFO or leave specific missing basis as needs user research.",
        },
        {
            "label": "Import warnings reviewed",
            "complete": import_warnings_reviewed,
            "detail": "All import warnings have reviewed decisions." if import_warnings_reviewed else "Review each warning and choose a decision.",
        },
        {
            "label": "Source overlap reviewed",
            "complete": source_overlaps_reviewed,
            "detail": "No overlapping source files detected." if source_overlaps_reviewed else "Review possible full-history/year-specific duplicate exports.",
        },
        {
            "label": "Missing basis reviewed",
            "complete": missing_basis_reviewed,
            "detail": "No missing acquisition basis remains." if missing_basis_reviewed else "Some sales still need earlier acquisition basis or user research.",
        },
        {
            "label": "Tax evidence inventory reviewed",
            "complete": tax_evidence_reviewed,
            "detail": "Year-level tax evidence is ready for review." if tax_evidence_reviewed else "Review filed returns, crypto totals, payment evidence, and zero/not-applicable confirmations by year.",
        },
        {
            "label": "Draft export acknowledged",
            "complete": bool(draft_acknowledged),
            "detail": "Draft output may be generated for review." if draft_acknowledged else "Required only when unresolved review items remain.",
        },
    ]


def get_audit_readiness_summary(transactions):
    if len(getattr(transactions, "transactions", [])) == 0:
        stats_rows = []
    else:
        date_range = get_transactions_date_range(transactions, {"start_date": "", "end_date": ""})
        stats_rows = get_stats_table_data_range(transactions, date_range)
    holdings_rows = get_multi_asset_holdings_reconciliation_table_data(transactions)
    form_8949_totals = get_form_8949_totals(transactions)
    import_warnings = getattr(transactions, "import_warnings", []) or []
    warning_rows = _import_warning_review_rows(import_warnings, transactions=transactions)
    unresolved_warning_rows = _unresolved_import_warning_rows(transactions)
    missing_basis_rows = get_missing_basis_review_rows(transactions)
    source_overlap_rows = _source_overlap_rows(transactions)
    tax_alignment = get_tax_filing_alignment_summary(transactions)
    tax_evidence_inventory = _tax_evidence_inventory_summary(transactions, tax_alignment)

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
        if row[6] == "Needs Review"
    ]
    basis_assets_needing_research = sorted({
        row["asset"]
        for row in missing_basis_rows
        if row["status"] == "Needs user research"
    })
    basis_assets_missing = sorted({
        row["asset"]
        for row in missing_basis_rows
        if row["status"] != "Needs user research"
    })
    blockers = []
    warnings = []

    if len(getattr(transactions, "transactions", [])) == 0:
        blockers.append("Import transactions before generating an audit packet.")

    if basis_assets_missing:
        blockers.append(
            "Missing acquisition basis before sales for: " + ", ".join(basis_assets_missing)
        )

    if basis_assets_needing_research:
        blockers.append(
            "Missing basis left as needs user research for: " + ", ".join(basis_assets_needing_research)
        )

    if assets_needing_holdings:
        blockers.append(
            "Record current holdings for: " + ", ".join(assets_needing_holdings)
        )

    if assets_with_mismatches:
        blockers.append(
            "Review holdings discrepancies for: " + ", ".join(assets_with_mismatches)
        )

    if unresolved_warning_rows:
        warnings.append(
            f"Choose review decisions for {len(unresolved_warning_rows)} import warning"
            f"{'s' if len(unresolved_warning_rows) != 1 else ''}."
        )

    if source_overlap_rows:
        warnings.append(
            f"Review {len(source_overlap_rows)} possible overlapping source file pair"
            f"{'s' if len(source_overlap_rows) != 1 else ''}."
        )

    if form_8949_totals["total"]["rows"] == 0 and any(row.get("num_sells", 0) > 0 for row in stats_rows):
        blockers.append("Sells exist, but no linked Form 8949-style rows can be generated yet.")

    filed_total_records = _missing_filed_total_records(tax_alignment, tax_evidence_inventory)
    if filed_total_records:
        blockers.append(
            "Review tax evidence inventory for: "
            + ", ".join(str(row["year"]) for row in filed_total_records)
        )

    is_ready = len(blockers) == 0 and len(warnings) == 0

    if blockers:
        status = "Not ready"
        status_class = "status-needs-review"
        missing_parts = []
        if missing_basis_rows:
            missing_parts.append("basis before these sales")
        if assets_needing_holdings or assets_with_mismatches:
            missing_parts.append("current holdings explanations for these assets")
        if unresolved_warning_rows:
            missing_parts.append("review decisions for these import warnings")
        if source_overlap_rows:
            missing_parts.append("review of possible overlapping source files")
        if filed_total_records:
            missing_parts.append("year-level tax evidence inventory")

        next_action = (
            "You are missing " + ", ".join(missing_parts) + "."
            if missing_parts
            else blockers[0]
        )
    elif warnings:
        status = "Review warnings"
        status_class = "status-unlinked-sales"
        next_action = warnings[0]
    else:
        status = "Ready for review"
        status_class = "status-verified"
        next_action = "Generate the audit packet, then review exported files against source records."

    return {
        "status": status,
        "status_class": status_class,
        "is_ready": is_ready,
        "next_action": next_action,
        "blockers": blockers,
        "warnings": warnings,
        "import_warnings": import_warnings,
        "import_warning_rows": warning_rows,
        "unresolved_import_warning_rows": unresolved_warning_rows,
        "missing_records": {
            "basis": missing_basis_rows,
            "current_holdings": _missing_current_holdings_records(holdings_rows),
            "holdings_explanations": _missing_holdings_explanation_records(holdings_rows),
            "filed_totals": filed_total_records,
            "tax_evidence": tax_evidence_inventory["review_rows"],
            "source_overlaps": source_overlap_rows,
        },
        "checklist": _reconciliation_checklist(
            transactions,
            holdings_rows,
            missing_basis_rows,
            unresolved_warning_rows,
            source_overlap_rows,
            tax_alignment,
            tax_evidence_inventory,
        ),
        "metrics": {
            "transactions": len(getattr(transactions, "transactions", [])),
            "assets": len(getattr(transactions, "assets", set())),
            "links": len(getattr(transactions, "links", set())),
            "assets_needing_holdings": len(assets_needing_holdings),
            "assets_with_mismatches": len(assets_with_mismatches),
            "assets_with_unlinked_sales": len(assets_with_unlinked_sales),
            "import_warnings": len(import_warnings),
            "unresolved_import_warnings": len(unresolved_warning_rows),
            "missing_basis_rows": len(missing_basis_rows),
            "source_overlaps": len(source_overlap_rows),
            "tax_evidence_years_needing_review": tax_evidence_inventory["metrics"]["years_needing_review"],
            "tax_evidence_items": tax_evidence_inventory["metrics"]["evidence_items"],
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
            "Tax filing review CSV and JSON",
            "Tax evidence inventory CSV and JSON",
            "Holdings reconciliation CSV",
            "Current holdings lots CSV",
            "Import warnings CSV with review decisions",
            "Missing basis review CSV",
            "Source overlap review CSV",
            "Copied source files when still available on disk",
            "Copied tax evidence files when evidence paths are available on disk",
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

    date_range = date_range or {}

    # Filter Transactions to date range. A missing start/end means "unbounded",
    # which is what an empty data set returns for All Time.
    filtered_transactions = [
        trans
        for trans in transactions
        if _date_in_range(trans.time_stamp, date_range)
    ]


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
        next_action = "Enter the current quantity you want Gainz to use for reconciliation. Keep source records for the amount entered."
        allocation_method = "No declared holdings are saved, so Gainz is showing unlinked buy and receive lots for review."
    else:
        difference = expected_holdings - declared_holdings
        allocation_method = (
            "Review estimate only: available lots are displayed using a FIFO-style assumption. "
            "Confirm final accounting treatment against source records or with a qualified tax professional."
        )

        if abs(difference) <= 0.00000001:
            status = "Verified"
            next_action = "No quantity difference was detected from imported buys and sells. Review source records, lots, and basis links before using generated reports."
        elif difference > 0:
            status = "Needs Review"
            if totals["send"] > 0:
                next_action = (
                    f"Review imported sends. If source records show up to {format_quantity(min(difference, totals['send']))} {asset} "
                    "left your ownership, classify those documented sends as disposals; owner transfers should remain transfers."
                )
            else:
                next_action = (
                    "Review whether the difference is explained by missing disposals, transfers, losses, or other records. "
                    "Reclassify activity only when supported by documentation."
                )
        else:
            status = "Needs Review"
            next_action = (
                "Review whether the difference is explained by missing acquisitions, income, gifts, transfers, or other records. "
                "Add or reclassify activity only when supported by documentation."
            )

    return {
        "asset": asset,
        "declared_holdings": declared_holdings,
        "buy_quantity": totals["buy"],
        "sell_quantity": totals["sell"],
        "send_quantity": totals["send"],
        "receive_quantity": totals["receive"],
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
        ["Imported Buy Quantity", format_quantity(reconciliation["buy_quantity"])],
        ["Imported Sell Quantity", format_quantity(reconciliation["sell_quantity"])],
        ["Calculated Net From Imported Buys/Sells", format_quantity(reconciliation["expected_holdings"])],
        ["Imported Net Including Transfers", format_quantity(reconciliation["imported_net"])],
        ["Available Buy/Receive Lot Quantity", format_quantity(reconciliation["available_lot_quantity"])],
        [
            "Review Difference vs Declared Holdings",
            format_quantity(reconciliation["difference"])
            if reconciliation["difference"] is not None
            else "N/A",
        ],
        ["Status", reconciliation["status"]],
        ["Review Guidance", reconciliation["next_action"]],
        ["Lot Allocation Assumption", reconciliation["lot_allocation_method"]],
    ]


def _holdings_source_name(source):
    source_text = str(source or "").replace("\\", os.sep)
    return os.path.basename(source_text) or "Manual"


def _holdings_delta_for_expected(trans):
    if trans.trans_type == "buy":
        return trans.quantity

    if trans.trans_type == "sell":
        return -trans.quantity

    return 0.0


def _holdings_delta_for_imported_net(trans):
    if trans.trans_type in ("buy", "receive"):
        return trans.quantity

    if trans.trans_type in ("sell", "send"):
        return -trans.quantity

    return 0.0


def _holdings_days_between(left, right):
    left_dt = comparable_datetime(left)
    right_dt = comparable_datetime(right)

    if hasattr(left_dt, "__sub__") and hasattr(right_dt, "__sub__"):
        try:
            return abs((left_dt - right_dt).days)
        except Exception:
            return None

    return None


def _holdings_quantity_match(left_quantity, right_quantity):
    left = abs(float(left_quantity or 0.0))
    right = abs(float(right_quantity or 0.0))
    absolute_delta = abs(left - right)

    if absolute_delta <= 0.00000001:
        return True

    larger = max(left, right, 0.00000001)
    return absolute_delta / larger <= 0.001


def _holdings_transfer_match(trans, candidates):
    best_match = None
    best_days = None

    for candidate in candidates:
        if not _holdings_quantity_match(trans.quantity, candidate.quantity):
            continue

        days = _holdings_days_between(trans.time_stamp, candidate.time_stamp)
        if days is None or days > 14:
            continue

        if best_days is None or days < best_days:
            best_match = candidate
            best_days = days

    return best_match, best_days


def _holdings_classification_review_rows(asset_transactions):
    sends = [trans for trans in asset_transactions if trans.trans_type == "send"]
    receives = [trans for trans in asset_transactions if trans.trans_type == "receive"]
    rows = []

    for trans in asset_transactions:
        if trans.trans_type not in ("send", "receive"):
            continue

        if trans.trans_type == "send":
            match, days = _holdings_transfer_match(trans, receives)
            if match:
                status = "Possible owner transfer"
                question = "Did this leave one account you own and appear in another account you own?"
                clues = (
                    f"Nearby receive found {format_quantity(match.quantity)} on "
                    f"{_format_report_datetime(match.time_stamp)} from {_holdings_source_name(match.source)}"
                    f" ({days} day{'s' if days != 1 else ''} apart)."
                )
                next_action = (
                    "If it was your own wallet/exchange transfer, leave it as a transfer. "
                    "If it was a sale, exchange, payment, fee, gift, or other ownership transfer, record a documented disposal."
                )
            else:
                status = "Needs classification"
                question = "Did this send go to your own wallet, or did it leave your ownership?"
                clues = "No nearby same-quantity receive was found in imported records."
                next_action = (
                    "Find the destination record. Import the receiving source or leave notes for an owner transfer; "
                    "record a documented disposal only when source records show ownership changed."
                )
        else:
            match, days = _holdings_transfer_match(trans, sends)
            if match:
                status = "Possible owner transfer"
                question = "Is this the receiving side of a transfer from your own wallet or exchange?"
                clues = (
                    f"Nearby send found {format_quantity(match.quantity)} on "
                    f"{_format_report_datetime(match.time_stamp)} from {_holdings_source_name(match.source)}"
                    f" ({days} day{'s' if days != 1 else ''} apart)."
                )
                next_action = (
                    "If it came from your own wallet/exchange, leave it as a transfer. "
                    "If it was a buy, income, reward, gift, or outside acquisition, add or classify the basis-supported transaction."
                )
            else:
                status = "Needs source/basis"
                question = "Was this an owner transfer, a buy from another exchange, income, reward, gift, or another acquisition?"
                clues = "No nearby same-quantity send was found in imported records."
                next_action = (
                    "Identify the source. Import the matching exchange/wallet file, add the missing buy, "
                    "or classify the receive as a documented buy only when basis records support it."
                )

        rows.append([
            _format_report_datetime(trans.time_stamp),
            trans.trans_type.title(),
            format_quantity(trans.quantity),
            currency(trans.usd_total),
            _holdings_source_name(trans.source),
            status,
            question,
            clues,
            next_action,
        ])

    return rows


def _holdings_reconciliation_interpretation(reconciliation):
    difference = reconciliation["difference"]
    asset = reconciliation["asset"]

    if reconciliation["declared_holdings"] is None:
        return f"Save declared {asset} holdings to calculate the difference."

    if abs(difference) <= 0.00000001:
        return "This asset is verified against imported buys and sells. Review lots, links, and source records before export."

    if difference > 0:
        if reconciliation["send_quantity"] > 0:
            recommended_quantity = min(difference, reconciliation["send_quantity"])
            return (
                f"The calculated net from imported buys and sells is higher than declared holdings by "
                f"{format_quantity(difference)} {asset}. Imported sends total "
                f"{format_quantity(reconciliation['send_quantity'])} {asset}. If source records show "
                f"{format_quantity(recommended_quantity)} {asset} of those sends left your ownership or were sent elsewhere "
                "and traded, classify only the documented quantity as disposals. Owner transfers should remain transfers."
            )

        return (
            "The calculated net from imported buys and sells is higher than declared holdings. Review sends, "
            "missing disposals, losses, transfers, or other records before using generated reports."
        )

    return (
        "Declared holdings are higher than imported buys and sells currently explain. Review missing acquisitions, income, "
        "gifts, transfers, or other records that may need basis support."
    )


def get_holdings_difference_breakdown(transactions, asset):
    asset = str(asset or "").upper()
    reconciliation = get_holdings_reconciliation(transactions, asset)
    declared_holdings = reconciliation["declared_holdings"]

    transaction_rows = []
    yearly_totals = {}
    running_expected = 0.0
    running_imported_net = 0.0

    asset_transactions = sorted(
        [
            trans
            for trans in transactions
            if trans.symbol == asset and trans.trans_type in ("buy", "sell", "send", "receive")
        ],
        key=lambda trans: comparable_datetime(trans.time_stamp),
    )

    for trans in asset_transactions:
        year = trans.time_stamp.year if hasattr(trans.time_stamp, "year") else str(trans.time_stamp)[:4]
        if year not in yearly_totals:
            yearly_totals[year] = {
                "buy": 0.0,
                "sell": 0.0,
                "send": 0.0,
                "receive": 0.0,
                "count": 0,
            }

        yearly_totals[year][trans.trans_type] += trans.quantity
        yearly_totals[year]["count"] += 1

        expected_delta = _holdings_delta_for_expected(trans)
        imported_net_delta = _holdings_delta_for_imported_net(trans)
        running_expected += expected_delta
        running_imported_net += imported_net_delta

        transaction_rows.append([
            _format_report_datetime(trans.time_stamp),
            trans.trans_type.title(),
            format_quantity(trans.quantity),
            currency(trans.usd_spot),
            currency(trans.usd_total),
            format_quantity(expected_delta),
            format_quantity(running_expected),
            format_quantity(imported_net_delta),
            format_quantity(running_imported_net),
            _holdings_source_name(trans.source),
        ])

    yearly_rows = []
    running_expected = 0.0
    running_imported_net = 0.0

    for year in sorted(yearly_totals):
        totals = yearly_totals[year]
        expected_delta = totals["buy"] - totals["sell"]
        imported_net_delta = totals["buy"] + totals["receive"] - totals["sell"] - totals["send"]
        running_expected += expected_delta
        running_imported_net += imported_net_delta

        yearly_rows.append([
            str(year),
            totals["count"],
            format_quantity(totals["buy"]),
            format_quantity(totals["sell"]),
            format_quantity(totals["send"]),
            format_quantity(totals["receive"]),
            format_quantity(expected_delta),
            format_quantity(running_expected),
            format_quantity(imported_net_delta),
            format_quantity(running_imported_net),
        ])

    expected_formula = (
        f"Buys {format_quantity(reconciliation['buy_quantity'])} - sells "
        f"{format_quantity(reconciliation['sell_quantity'])} = "
        f"{format_quantity(reconciliation['expected_holdings'])} {asset} calculated from imported buys/sells only."
    )
    transfer_formula = (
        f"Including transfers: buys {format_quantity(reconciliation['buy_quantity'])} + receives "
        f"{format_quantity(reconciliation['receive_quantity'])} - sells "
        f"{format_quantity(reconciliation['sell_quantity'])} - sends "
        f"{format_quantity(reconciliation['send_quantity'])} = "
        f"{format_quantity(reconciliation['imported_net'])} {asset} imported net after transfers."
    )

    if declared_holdings is None:
        difference_formula = f"No declared {asset} holdings are saved yet."
    else:
        difference_formula = (
            f"Expected {format_quantity(reconciliation['expected_holdings'])} - declared "
            f"{format_quantity(declared_holdings)} = "
            f"{format_quantity(reconciliation['difference'])} {asset} review difference vs declared holdings."
        )

    recommended_disposal_quantity = None
    if (
        declared_holdings is not None
        and reconciliation["difference"] is not None
        and reconciliation["difference"] > 0.00000001
        and reconciliation["send_quantity"] > 0.00000001
    ):
        recommended_disposal_quantity = min(
            reconciliation["difference"],
            reconciliation["send_quantity"],
        )

    return {
        "summary": {
            "asset": asset,
            "declared_holdings": (
                format_quantity(declared_holdings)
                if declared_holdings is not None
                else "N/A"
            ),
            "buy_quantity": format_quantity(reconciliation["buy_quantity"]),
            "sell_quantity": format_quantity(reconciliation["sell_quantity"]),
            "send_quantity": format_quantity(reconciliation["send_quantity"]),
            "receive_quantity": format_quantity(reconciliation["receive_quantity"]),
            "expected_holdings": format_quantity(reconciliation["expected_holdings"]),
            "imported_net": format_quantity(reconciliation["imported_net"]),
            "difference": (
                format_quantity(reconciliation["difference"])
                if reconciliation["difference"] is not None
                else "N/A"
            ),
            "recommended_disposal_quantity": (
                format_quantity(recommended_disposal_quantity)
                if recommended_disposal_quantity is not None
                else "N/A"
            ),
            "has_send_disposal_recommendation": recommended_disposal_quantity is not None,
            "status": reconciliation["status"],
            "basis_review_status": (_basis_review_note(transactions, asset) or {}).get("status", ""),
            "basis_review_note": (_basis_review_note(transactions, asset) or {}).get("note", ""),
            "transaction_count": len(asset_transactions),
            "expected_formula": expected_formula,
            "difference_formula": difference_formula,
            "transfer_formula": transfer_formula,
            "interpretation": _holdings_reconciliation_interpretation(reconciliation),
        },
        "yearly_rows": yearly_rows,
        "transaction_rows": transaction_rows,
        "classification_rows": _holdings_classification_review_rows(asset_transactions),
    }


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
                time_stamp = parse_gainz_datetime(time_stamp)
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


