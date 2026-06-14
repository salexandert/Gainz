import os
import re
from collections import defaultdict
from datetime import date, datetime, time
from itertools import combinations


YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def _source_name(source):
    source = str(source or "Manual / Unknown")
    return os.path.basename(source.replace("\\", os.sep)) or source


def _source_family_key(source):
    name = os.path.splitext(_source_name(source).lower())[0]
    name = YEAR_RE.sub("", name)
    return re.sub(r"[^a-z0-9]+", "", name)


def _source_years(source):
    return sorted(set(YEAR_RE.findall(_source_name(source))))


def _date_value(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    if isinstance(value, date):
        return datetime.combine(value, time.min)

    if hasattr(value, "to_pydatetime"):
        return _date_value(value.to_pydatetime())

    try:
        return value.replace(tzinfo=None)
    except (AttributeError, TypeError):
        return value


def _date_label(value):
    value = _date_value(value)
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value or "N/A")


def _date_ranges_overlap(left, right):
    if not left["first"] or not right["first"]:
        return False

    return left["first"] <= right["last"] and right["first"] <= left["last"]


def _signature(transaction):
    time_stamp = _date_value(getattr(transaction, "time_stamp", None))
    date_key = time_stamp.date().isoformat() if hasattr(time_stamp, "date") else str(time_stamp)
    return (
        getattr(transaction, "symbol", ""),
        getattr(transaction, "trans_type", ""),
        date_key,
        round(float(getattr(transaction, "quantity", 0) or 0), 8),
    )


def _source_groups(transactions):
    groups = defaultdict(list)
    for transaction in getattr(transactions, "transactions", []) or []:
        source = str(getattr(transaction, "source", "") or "Manual / Unknown")
        groups[source].append(transaction)
    return groups


def _source_stats(source, rows):
    timestamps = [
        _date_value(getattr(transaction, "time_stamp", None))
        for transaction in rows
        if getattr(transaction, "time_stamp", None) is not None
    ]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    first = min(timestamps) if timestamps else None
    last = max(timestamps) if timestamps else None

    return {
        "source": source,
        "name": _source_name(source),
        "family": _source_family_key(source),
        "years": _source_years(source),
        "count": len(rows),
        "first": first,
        "last": last,
        "date_range": f"{_date_label(first)} to {_date_label(last)}" if first and last else "N/A",
        "assets": sorted({getattr(transaction, "symbol", "") for transaction in rows if getattr(transaction, "symbol", "")}),
        "rows": rows,
    }


def _matching_signature_count(left_rows, right_rows):
    left_signatures = [_signature(transaction) for transaction in left_rows]
    right_signatures = set(_signature(transaction) for transaction in right_rows)
    return sum(1 for signature in left_signatures if signature in right_signatures)


def _overlap_message(left, right, matching_count, overlap_ratio, same_family, full_history_pair):
    if full_history_pair:
        return (
            f"{left['name']} and {right['name']} look like the same export family, "
            "with one file possibly being a full-history export and the other year-specific."
        )

    if overlap_ratio >= 0.35:
        return (
            f"{matching_count} transaction signature(s) appear in both source files. "
            "This can happen when overlapping exports are imported together."
        )

    if same_family:
        return (
            f"{left['name']} and {right['name']} share a source family and overlapping date ranges."
        )

    return "These source files have overlapping transaction signatures."


def detect_source_overlaps(transactions):
    groups = _source_groups(transactions)
    stats = [
        _source_stats(source, rows)
        for source, rows in groups.items()
        if len(rows) > 0
    ]
    overlaps = []

    for left, right in combinations(stats, 2):
        smaller, larger = (left, right) if left["count"] <= right["count"] else (right, left)
        matching_count = _matching_signature_count(smaller["rows"], larger["rows"])
        compared_count = max(1, smaller["count"])
        overlap_ratio = matching_count / compared_count
        same_family = bool(left["family"] and left["family"] == right["family"])
        date_overlap = _date_ranges_overlap(left, right)
        full_history_pair = same_family and bool(left["years"]) != bool(right["years"]) and date_overlap

        if not (
            overlap_ratio >= 0.35
            or full_history_pair
            or (same_family and date_overlap and matching_count > 0)
        ):
            continue

        status = "Likely full-history overlap" if full_history_pair else "Possible duplicate overlap"
        overlaps.append({
            "source_a": left["source"],
            "source_b": right["source"],
            "name_a": left["name"],
            "name_b": right["name"],
            "count_a": left["count"],
            "count_b": right["count"],
            "date_range_a": left["date_range"],
            "date_range_b": right["date_range"],
            "matching_rows": matching_count,
            "overlap_ratio": round(overlap_ratio, 4),
            "overlap_percent": f"{round(overlap_ratio * 100)}%",
            "status": status,
            "message": _overlap_message(left, right, matching_count, overlap_ratio, same_family, full_history_pair),
            "next_action": (
                "Open the source files and decide whether one is a full-history export that covers the other. "
                "If so, remove the duplicate/overlapping source from current data and keep the original file for evidence."
            ),
        })

    overlaps.sort(key=lambda row: (row["status"], row["name_a"], row["name_b"]))
    return overlaps


def sources_with_overlaps(overlaps):
    sources = set()
    for overlap in overlaps or []:
        sources.add(overlap["source_a"])
        sources.add(overlap["source_b"])
    return sources
