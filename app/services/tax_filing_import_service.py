import csv
import re

from utils import parse_float_value


HYPHEN_RE = re.compile(r"[\u2010-\u2015\u2212]+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

YEAR_ALIASES = ("tax year", "year", "filing year")
SHORT_PROCEEDS_ALIASES = ("short term proceeds", "short-term proceeds", "short proceeds")
LONG_PROCEEDS_ALIASES = ("long term proceeds", "long-term proceeds", "long proceeds")
SHORT_COST_ALIASES = ("short term cost basis", "short-term cost basis", "short cost basis")
LONG_COST_ALIASES = ("long term cost basis", "long-term cost basis", "long cost basis")
SHORT_GAIN_ALIASES = ("short term gain", "short-term gain", "short gain", "short term gain loss")
LONG_GAIN_ALIASES = ("long term gain", "long-term gain", "long gain", "long term gain loss")
TOTAL_PROCEEDS_ALIASES = ("reported proceeds", "total proceeds", "proceeds")
TOTAL_COST_ALIASES = ("reported cost basis", "total cost basis", "cost basis")
TOTAL_GAIN_ALIASES = ("reported gain loss", "reported gain/loss", "total gain loss", "gain loss", "gain/loss")
TAX_PAID_ALIASES = ("tax paid", "taxes paid", "amount paid", "payment amount", "balance paid")


def _normalized_key(value):
    text = HYPHEN_RE.sub("-", str(value or "").strip().lower())
    text = text.replace("/", " ")
    return NON_ALNUM_RE.sub(" ", text).strip()


def _field_lookup(fieldnames):
    return {
        _normalized_key(field): field
        for field in fieldnames or []
        if str(field or "").strip()
    }


def _row_value(row, lookup, aliases):
    for alias in aliases:
        source_key = lookup.get(_normalized_key(alias))
        if source_key and row.get(source_key) not in (None, ""):
            return row.get(source_key)

    return None


def _parse_money_or_none(value):
    if value in (None, ""):
        return None

    text = str(value).strip()
    if not text:
        return None

    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    parsed = parse_float_value(text)
    if parsed is None:
        return None
    return -parsed if negative else parsed


def _sum_values(*values):
    parsed_values = [
        value
        for value in (_parse_money_or_none(item) for item in values)
        if value is not None
    ]
    if not parsed_values:
        return None

    return sum(parsed_values)


def _first_money(row, lookup, aliases):
    return _parse_money_or_none(_row_value(row, lookup, aliases))


def _parse_year(value):
    if value in (None, ""):
        return None

    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def tax_total_records_from_csv(file_obj):
    if hasattr(file_obj, "stream"):
        file_obj = file_obj.stream

    if hasattr(file_obj, "read"):
        position = file_obj.tell() if hasattr(file_obj, "tell") else None
        content = file_obj.read()
        if position is not None and hasattr(file_obj, "seek"):
            file_obj.seek(position)
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig", errors="replace")
        rows = csv.DictReader(content.splitlines())
    else:
        rows = csv.DictReader(file_obj)

    lookup = _field_lookup(rows.fieldnames)
    records = []
    summary = {
        "total_rows": 0,
        "imported_count": 0,
        "skipped_count": 0,
        "skipped_missing_year": 0,
        "skipped_missing_totals": 0,
    }

    for row in rows:
        if not any(str(value or "").strip() for value in row.values()):
            continue

        summary["total_rows"] += 1
        year = _parse_year(_row_value(row, lookup, YEAR_ALIASES))
        if year is None:
            summary["skipped_count"] += 1
            summary["skipped_missing_year"] += 1
            continue

        reported_proceeds = _sum_values(
            _row_value(row, lookup, SHORT_PROCEEDS_ALIASES),
            _row_value(row, lookup, LONG_PROCEEDS_ALIASES),
        )
        reported_cost_basis = _sum_values(
            _row_value(row, lookup, SHORT_COST_ALIASES),
            _row_value(row, lookup, LONG_COST_ALIASES),
        )
        reported_gain_loss = _sum_values(
            _row_value(row, lookup, SHORT_GAIN_ALIASES),
            _row_value(row, lookup, LONG_GAIN_ALIASES),
        )

        if reported_proceeds is None:
            reported_proceeds = _first_money(row, lookup, TOTAL_PROCEEDS_ALIASES)
        if reported_cost_basis is None:
            reported_cost_basis = _first_money(row, lookup, TOTAL_COST_ALIASES)
        if reported_gain_loss is None:
            reported_gain_loss = _first_money(row, lookup, TOTAL_GAIN_ALIASES)

        total_values = [reported_proceeds, reported_cost_basis, reported_gain_loss]
        if all(value is None for value in total_values):
            summary["skipped_count"] += 1
            summary["skipped_missing_totals"] += 1
            continue

        records.append({
            "year": year,
            "reported_proceeds": reported_proceeds if reported_proceeds is not None else 0.0,
            "reported_cost_basis": reported_cost_basis if reported_cost_basis is not None else 0.0,
            "reported_gain_loss": reported_gain_loss if reported_gain_loss is not None else 0.0,
            "tax_paid": _first_money(row, lookup, TAX_PAID_ALIASES),
        })

    summary["imported_count"] = len(records)
    return records, summary


def import_tax_total_records(file_obj, transactions, evidence_reference):
    records, summary = tax_total_records_from_csv(file_obj)
    for record in records:
        existing_record = transactions.get_tax_year_record(record["year"])
        transactions.set_tax_year_record(
            year=record["year"],
            reported_proceeds=record["reported_proceeds"],
            reported_cost_basis=record["reported_cost_basis"],
            reported_gain_loss=record["reported_gain_loss"],
            tax_paid=record["tax_paid"] if record["tax_paid"] is not None else (existing_record or {}).get("tax_paid"),
            filing_status="Filed",
            evidence_reference=evidence_reference,
            notes=f"Imported from filed totals CSV. Source rows imported in this batch: {summary['imported_count']}.",
        )
        if hasattr(transactions, "set_tax_evidence_record"):
            transactions.set_tax_evidence_record(
                year=record["year"],
                evidence_type="crypto_workbook",
                evidence_label=evidence_reference,
                notes="Filed totals CSV imported into Tax Filing Review.",
            )

    return summary
