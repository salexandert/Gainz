import csv
import os
import re


ROW_WARNING_RE = re.compile(
    r"^(?P<verb>Skipped|Imported) row (?P<row>\d+) from (?P<source>[^:]+?)(?::| with )\s*(?P<detail>.*)$",
    re.IGNORECASE,
)
UNRECOGNIZED_TYPE_RE = re.compile(r"unrecognized transaction type '([^']+)'", re.IGNORECASE)
IMPORT_WARNING_DECISIONS = {
    "true_zero_value_transfer": {
        "label": "Own wallet/account transfer",
        "status": "Resolved",
        "resolved": True,
    },
    "needs_manual_usd_value": {
        "label": "Sold, spent, or paid to someone",
        "status": "Needs value or evidence",
        "resolved": False,
    },
    "ignore_for_now": {
        "label": "Leave unresolved for draft only",
        "status": "Draft-only unresolved",
        "resolved": False,
    },
    "note": {
        "label": "Note added",
        "status": "Needs review",
        "resolved": False,
    },
    "unknown_needs_research": {
        "label": "I do not know yet",
        "status": "Needs research",
        "resolved": False,
    },
    "cleared_by_source_update": {
        "label": "Cleared by source update",
        "status": "Cleared",
        "resolved": True,
    },
}


def _source_name(value):
    source = str(value or "").strip()
    return os.path.basename(source) or source or "Unknown source"


def _candidate_source_paths(transactions, source_name):
    source_name = _source_name(source_name)
    candidates = []

    if os.path.exists(source_name):
        candidates.append(source_name)

    for transaction in getattr(transactions, "transactions", []) if transactions else []:
        source = str(getattr(transaction, "source", "") or "")
        if not source:
            continue
        if os.path.basename(source) == source_name and os.path.exists(source):
            candidates.append(source)

    seen = set()
    unique_candidates = []
    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(normalized)

    return unique_candidates


def _read_csv_row_details(source_name, row_number, transactions=None):
    if str(row_number or "").upper() == "N/A":
        return {}

    try:
        row_number = int(row_number)
    except (TypeError, ValueError):
        return {}

    source_paths = _candidate_source_paths(transactions, source_name)
    if not source_paths:
        return {}

    source_path = source_paths[0]
    try:
        from parsers import (
            analyze_csv_import,
            build_column_lookup,
            get_row_value,
            normalize_asset_symbol,
            parse_quantity_value,
            standardize_transaction_type,
        )

        with open(source_path, newline="", encoding="utf-8-sig", errors="replace") as file:
            rows = list(csv.reader(file))

        if row_number < 1 or row_number > len(rows):
            return {"source_path": source_path}

        analysis = analyze_csv_import(source_path)
        header_row = max(int(analysis.get("header_row") or 1), 1)
        if header_row > len(rows):
            header_row = 1

        headers = [str(value or "").strip() for value in rows[header_row - 1]]
        values = rows[row_number - 1]
        row = {
            headers[index]: values[index] if index < len(values) else ""
            for index in range(len(headers))
        }
        lookup = build_column_lookup(headers)
        raw_type = get_row_value(row, lookup, "transaction_type", "")
        raw_quantity = get_row_value(row, lookup, "asset_amount", "")
        raw_asset = get_row_value(row, lookup, "asset_type", "")
        raw_usd_amount = (
            get_row_value(row, lookup, "fiat_amount", "")
            or get_row_value(row, lookup, "total", "")
            or get_row_value(row, lookup, "net_amount", "")
            or get_row_value(row, lookup, "subtotal", "")
        )
        asset = normalize_asset_symbol(raw_asset)
        quantity = str(parse_quantity_value(raw_quantity)) if raw_quantity != "" else ""
        nearby_row = _nearby_source_row(
            rows,
            headers,
            lookup,
            header_row,
            row_number,
            asset,
            quantity,
            normalize_asset_symbol,
            parse_quantity_value,
            standardize_transaction_type,
            get_row_value,
        )

        return {
            "source_path": source_path,
            "row_date": str(get_row_value(row, lookup, "date", "") or ""),
            "row_type": standardize_transaction_type(raw_type),
            "raw_row_type": str(raw_type or ""),
            "asset": asset,
            "quantity": quantity,
            "raw_usd_amount": str(raw_usd_amount or ""),
            "notes": str(get_row_value(row, lookup, "notes", "") or ""),
            "nearby_row": nearby_row,
        }
    except Exception:
        return {"source_path": source_path}


def _nearby_source_row(
    rows,
    headers,
    lookup,
    header_row,
    row_number,
    asset,
    quantity,
    normalize_asset_symbol,
    parse_quantity_value,
    standardize_transaction_type,
    get_row_value,
):
    if not rows or row_number <= 1:
        return None

    for candidate_number in (row_number + 1, row_number - 1):
        if candidate_number <= header_row or candidate_number > len(rows):
            continue

        values = rows[candidate_number - 1]
        row = {
            headers[index]: values[index] if index < len(values) else ""
            for index in range(len(headers))
        }
        raw_type = get_row_value(row, lookup, "transaction_type", "")
        candidate_type = standardize_transaction_type(raw_type)
        candidate_asset = normalize_asset_symbol(get_row_value(row, lookup, "asset_type", ""))
        raw_quantity = get_row_value(row, lookup, "asset_amount", "")
        candidate_quantity = str(parse_quantity_value(raw_quantity)) if raw_quantity != "" else ""

        if asset and candidate_asset and candidate_asset != asset:
            continue
        if quantity and candidate_quantity and candidate_quantity != quantity:
            continue
        if candidate_type not in ("Buy", "Sell", "Receive", "Send"):
            continue

        raw_usd_amount = (
            get_row_value(row, lookup, "fiat_amount", "")
            or get_row_value(row, lookup, "total", "")
            or get_row_value(row, lookup, "net_amount", "")
            or get_row_value(row, lookup, "subtotal", "")
        )
        return {
            "row": str(candidate_number),
            "row_type": candidate_type,
            "raw_row_type": str(raw_type or ""),
            "asset": candidate_asset,
            "quantity": candidate_quantity,
            "raw_usd_amount": str(raw_usd_amount or ""),
            "notes": str(get_row_value(row, lookup, "notes", "") or ""),
        }

    return None


def _likely_category(issue, row_details):
    row_type = str(row_details.get("row_type", "") or "").lower()
    issue_lower = str(issue or "").lower()

    if "$0 usd spot" in issue_lower:
        if row_type in ("send", "receive"):
            return "Possible owner transfer or missing USD value"
        if row_type in ("buy", "sell"):
            return "Likely missing USD value"
        return "Zero-value or missing-price row"

    if "unrecognized transaction type" in issue_lower:
        return "Needs transaction classification"

    if "required columns" in issue_lower:
        return "Needs column mapping"

    return "Needs source-row review"


def _warning_guidance(issue, row_details):
    issue_lower = str(issue or "").lower()
    row_type = str(row_details.get("row_type", "") or "")
    raw_type = str(row_details.get("raw_row_type", "") or row_type or "source row")
    asset = row_details.get("asset") or "asset"
    quantity = row_details.get("quantity") or ""
    is_zero_usd = "$0 usd spot" in issue_lower
    is_transfer_like = row_type in ("Send", "Receive") or any(
        term in raw_type.lower()
        for term in ("withdraw", "deposit", "send", "receive", "transfer")
    )

    if is_zero_usd and is_transfer_like:
        direction = "withdrawal" if row_type == "Send" or "withdraw" in raw_type.lower() else "transfer"
        nearby = row_details.get("nearby_row") or {}
        nearby_summary = ""
        if nearby:
            nearby_type = nearby.get("raw_row_type") or nearby.get("row_type") or "nearby row"
            nearby_quantity = nearby.get("quantity") or quantity
            nearby_asset = nearby.get("asset") or asset
            nearby_usd = nearby.get("raw_usd_amount") or ""
            nearby_summary = (
                f"Nearby source row: row {nearby.get('row')}: {nearby_type}, "
                f"{nearby_quantity} {nearby_asset}"
            )
            if nearby_usd:
                nearby_summary = f"{nearby_summary}, {nearby_usd}"
            nearby_summary = f"{nearby_summary}."

        return {
            "mode": "zero_usd_transfer",
            "card_title": f"Gainz found a $0 {asset} {direction}",
            "summary": (
                f"This looks like a {asset} {direction}. If it went to your own wallet or account, "
                "it can stay as a transfer. If it was sold, spent, or paid to someone, Gainz needs "
                "a USD value or supporting note before reports are filing-ready."
            ),
            "question": f"What happened to this {asset}?",
            "nearby_summary": nearby_summary,
            "decision_options": [
                {
                    "decision": "true_zero_value_transfer",
                    "label": "This went to my own wallet/account",
                    "style": "primary",
                },
                {
                    "decision": "needs_manual_usd_value",
                    "label": "This was sold, spent, or paid to someone",
                    "style": "secondary",
                },
                {
                    "decision": "unknown_needs_research",
                    "label": "I do not know yet",
                    "style": "secondary",
                },
                {
                    "decision": "ignore_for_now",
                    "label": "Leave unresolved for draft only",
                    "style": "quiet",
                },
            ],
        }

    if is_zero_usd and row_type in ("Buy", "Sell"):
        return {
            "mode": "missing_usd_value",
            "card_title": f"Gainz found a $0 USD {row_type.lower()} row",
            "summary": (
                "This row looks like taxable activity or basis activity with a missing USD value. "
                "Open the source row, check the USD columns, and enter or re-import the correct value."
            ),
            "question": "Can you find the missing USD value?",
            "nearby_summary": "",
            "decision_options": [
                {
                    "decision": "needs_manual_usd_value",
                    "label": "This row needs a USD value",
                    "style": "primary",
                },
                {
                    "decision": "unknown_needs_research",
                    "label": "I do not know yet",
                    "style": "secondary",
                },
                {
                    "decision": "ignore_for_now",
                    "label": "Leave unresolved for draft only",
                    "style": "quiet",
                },
            ],
        }

    return {
        "mode": "import_repair",
        "card_title": "Gainz found an import row that needs review",
        "summary": (
            "Review the source row and decide whether this is a missing value, a row that should "
            "be imported differently, or a research item."
        ),
        "question": "What should happen with this row?",
        "nearby_summary": "",
        "decision_options": [
            {
                "decision": "needs_manual_usd_value",
                "label": "This needs a corrected value",
                "style": "primary",
            },
            {
                "decision": "unknown_needs_research",
                "label": "I do not know yet",
                "style": "secondary",
            },
            {
                "decision": "ignore_for_now",
                "label": "Leave unresolved for draft only",
                "style": "quiet",
            },
        ],
    }


def _review_for_warning(transactions, raw_message):
    if transactions is not None and hasattr(transactions, "get_import_warning_review"):
        return transactions.get_import_warning_review(raw_message) or {}

    return {}


def _decision_state(review_record):
    decision = str(review_record.get("decision", "") or "")
    state = IMPORT_WARNING_DECISIONS.get(decision, {})

    return {
        "decision": decision,
        "decision_label": state.get("label", "Not reviewed" if not decision else decision),
        "review_status": state.get("status", "Needs review"),
        "is_resolved": bool(state.get("resolved", False)),
        "review_note": review_record.get("note", "") or "",
        "review_updated_at": review_record.get("updated_at", "") or "",
    }


def classify_import_warning(message, transactions=None):
    raw_message = str(message or "").strip()
    lower_message = raw_message.lower()
    match = ROW_WARNING_RE.match(raw_message)
    source = _source_name(match.group("source")) if match else "Current import"
    row_number = match.group("row") if match else "N/A"
    detail = match.group("detail").strip() if match else raw_message
    issue = detail or raw_message
    status = "Needs review"
    next_action = (
        f"Open the source file and check row {row_number} plus the relevant mapped columns. "
        "If the row or column mapping is wrong, remove this source and re-import using "
        "Advanced Import. If it belongs in Gainz but the source cannot be fixed, add a "
        "source-backed manual transaction."
    )

    if "$0 usd spot price" in lower_message or "usd spot price" in lower_message:
        issue = "$0 USD spot price"
        status = "Price review"
        next_action = (
            f"Open the source file and check row {row_number} and the USD spot/total USD value "
            "column. If the row has a USD value or the wrong column was mapped, remove this "
            "source and re-import using Advanced Import with the correct USD spot price or total "
            "USD value column. If the row was truly zero-value, keep documentation with the "
            "source file."
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
                f"Open the source file and check row {row_number} plus the type, asset, quantity, "
                "and USD columns. If the row should be imported, remove this source and re-import "
                "using Advanced Import, or add a source-backed manual transaction."
            )
    elif "could not identify required columns" in lower_message:
        issue = "Required columns were not identified"
        status = "Mapping needed"
        next_action = (
            "Open the source file, confirm the header row and the date, type, asset, quantity, "
            "and USD value columns, then re-import using Advanced Import."
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

    row_details = _read_csv_row_details(source, row_number, transactions)
    decision = _decision_state(_review_for_warning(transactions, raw_message))
    guidance = _warning_guidance(issue, row_details)

    return {
        "raw": raw_message,
        "source": source,
        "row": row_number,
        "row_date": row_details.get("row_date", ""),
        "row_type": row_details.get("row_type", ""),
        "raw_row_type": row_details.get("raw_row_type", ""),
        "asset": row_details.get("asset", ""),
        "quantity": row_details.get("quantity", ""),
        "raw_usd_amount": row_details.get("raw_usd_amount", ""),
        "notes": row_details.get("notes", ""),
        "source_path": row_details.get("source_path", ""),
        "nearby_row": row_details.get("nearby_row"),
        "likely_category": _likely_category(issue, row_details),
        "issue": issue,
        "status": status,
        "next_action": next_action,
        **guidance,
        **decision,
    }


def import_warning_review_rows(warnings, transactions=None):
    return [classify_import_warning(warning, transactions=transactions) for warning in warnings or []]


def import_warning_audit_rows(transactions):
    active_warnings = list(getattr(transactions, "import_warnings", []) or [])
    active_set = set(active_warnings)
    rows = []
    for row in import_warning_review_rows(active_warnings, transactions=transactions):
        row["active_status"] = "Active"
        rows.append(row)

    for review in getattr(transactions, "import_warning_reviews", []) or []:
        warning = review.get("warning")
        if not warning or warning in active_set:
            continue

        row = classify_import_warning(warning, transactions=transactions)
        row["active_status"] = "Cleared from active warnings"
        row["next_action"] = (
            "This warning is no longer active in the current save. The historical review "
            "decision is preserved for the audit trail."
        )
        rows.append(row)

    return rows


def unresolved_import_warning_rows(transactions):
    return [
        row
        for row in import_warning_review_rows(
            getattr(transactions, "import_warnings", []) or [],
            transactions=transactions,
        )
        if not row.get("is_resolved")
    ]


def warning_matches_source(warning, source):
    source_name = _source_name(source)
    warning_text = str(warning or "")
    return bool(source_name and source_name in warning_text)


def clear_import_warnings_for_source(transactions, source):
    warnings = list(getattr(transactions, "import_warnings", []) or [])
    removed_warnings = [
        warning
        for warning in warnings
        if warning_matches_source(warning, source)
    ]
    transactions.import_warnings = [
        warning
        for warning in warnings
        if not warning_matches_source(warning, source)
    ]
    if removed_warnings:
        for warning in removed_warnings:
            if transactions.get_import_warning_review(warning):
                continue
            transactions.set_import_warning_review(
                warning,
                decision="cleared_by_source_update",
                note=(
                    "Warning removed from the active list when its source was re-imported "
                    "or removed. Review the current source records before relying on reports."
                ),
            )
