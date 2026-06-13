import os
import re


ROW_WARNING_RE = re.compile(
    r"^(?P<verb>Skipped|Imported) row (?P<row>\d+) from (?P<source>[^:]+?)(?::| with )\s*(?P<detail>.*)$",
    re.IGNORECASE,
)
UNRECOGNIZED_TYPE_RE = re.compile(r"unrecognized transaction type '([^']+)'", re.IGNORECASE)


def _source_name(value):
    source = str(value or "").strip()
    return os.path.basename(source) or source or "Unknown source"


def classify_import_warning(message):
    raw_message = str(message or "").strip()
    lower_message = raw_message.lower()
    match = ROW_WARNING_RE.match(raw_message)
    source = _source_name(match.group("source")) if match else "Current import"
    row_number = match.group("row") if match else "N/A"
    detail = match.group("detail").strip() if match else raw_message
    issue = detail or raw_message
    status = "Needs review"
    next_action = (
        "Review the source row. If it should affect holdings or generated reports, "
        "fix the CSV mapping, re-import the source, or add a source-backed manual transaction."
    )

    if "$0 usd spot price" in lower_message or "usd spot price" in lower_message:
        issue = "$0 USD spot price"
        status = "Price review"
        next_action = (
            "If the row has a USD value, remove this source and re-import with a mapped USD spot "
            "price or total USD value column. If the row was truly zero-value, keep documentation "
            "with the source file."
        )
    elif "unrecognized transaction type" in lower_message:
        type_match = UNRECOGNIZED_TYPE_RE.search(raw_message)
        transaction_type = type_match.group(1) if type_match else "unknown"
        issue = f"Unrecognized transaction type: {transaction_type}"
        status = "Classification review"

        if "coinbase earn" in lower_message:
            next_action = (
                "Coinbase Earn rows are now treated as receive/reward activity. Remove and re-import "
                "this source so those rows are included, then review holdings reconciliation."
            )
        else:
            next_action = (
                "Decide whether this row is a buy, sell, send, or receive. If it belongs in Gainz, "
                "use column review or add a manual transaction with the source row as support."
            )
    elif "could not identify required columns" in lower_message:
        issue = "Required columns were not identified"
        status = "Mapping needed"
        next_action = (
            "Upload the file again with column review enabled, choose the header row, and map date, "
            "type, asset, quantity, and USD value columns."
        )
    elif "missing or non-crypto asset" in lower_message:
        issue = "Missing or non-crypto asset"
        status = "Skipped row"
        next_action = (
            "Confirm whether this source row is fiat-only. If it contains crypto activity, map the "
            "asset symbol column or add the transaction manually."
        )
    elif "could not parse this row" in lower_message:
        issue = "Could not parse row"
        status = "Row review"
        next_action = (
            "Check the source row's date, type, quantity, and USD value. Correct the CSV or add a "
            "manual transaction if the row should be included."
        )
    elif "missing one of the required import columns" in lower_message:
        issue = "Missing required row value"
        status = "Row review"
        next_action = "Review the source row for blank required fields, then correct the CSV or add it manually."
    elif "currently imports csv files" in lower_message:
        issue = "Unsupported file type"
        status = "Import blocked"
        next_action = "Export or save the source data as CSV, then import it again."

    return {
        "raw": raw_message,
        "source": source,
        "row": row_number,
        "issue": issue,
        "status": status,
        "next_action": next_action,
    }


def import_warning_review_rows(warnings):
    return [classify_import_warning(warning) for warning in warnings or []]


def warning_matches_source(warning, source):
    source_name = _source_name(source)
    warning_text = str(warning or "")
    return bool(source_name and source_name in warning_text)


def clear_import_warnings_for_source(transactions, source):
    warnings = list(getattr(transactions, "import_warnings", []) or [])
    transactions.import_warnings = [
        warning
        for warning in warnings
        if not warning_matches_source(warning, source)
    ]
