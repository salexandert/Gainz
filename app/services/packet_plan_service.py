import os
from pathlib import Path


def transaction_source_paths(transactions):
    sources = set()
    for transaction in getattr(transactions, "transactions", []) or []:
        source = getattr(transaction, "source", "")
        if source and os.path.exists(str(source)):
            sources.add(str(source))
    return sorted(sources)


def tax_evidence_packet_counts(transactions):
    counts = {
        "copied": 0,
        "reference_only": 0,
        "missing": 0,
        "total": 0,
    }

    for record in getattr(transactions, "tax_evidence_records", []) or []:
        counts["total"] += 1
        evidence_path = str(record.get("evidence_path") or "")
        source_path = Path(evidence_path) if evidence_path else None
        source_exists = bool(source_path and source_path.exists() and source_path.is_file())

        if record.get("copy_to_packet") and source_exists:
            counts["copied"] += 1
        elif evidence_path and not source_exists:
            counts["missing"] += 1
        else:
            counts["reference_only"] += 1

    return counts


def get_packet_preview(transactions, readiness, output_dir):
    source_paths = transaction_source_paths(transactions)
    evidence_counts = tax_evidence_packet_counts(transactions)
    is_ready = bool(readiness.get("is_ready"))
    packet_prefix = "gainz_audit_packet" if is_ready else "gainz_audit_packet_DRAFT"
    unresolved_items = list(readiness.get("blockers") or []) + list(readiness.get("warnings") or [])
    unresolved_groups = list(readiness.get("blocker_groups") or [])

    return {
        "status": "Filing-ready review packet" if is_ready else "Draft packet",
        "status_class": readiness.get("status_class", ""),
        "is_draft": not is_ready,
        "copied_files_count": len(source_paths) + evidence_counts["copied"],
        "transaction_source_files_count": len(source_paths),
        "copied_tax_evidence_count": evidence_counts["copied"],
        "reference_only_files_count": evidence_counts["reference_only"],
        "missing_tax_evidence_count": evidence_counts["missing"],
        "unresolved_blocker_count": len(unresolved_items),
        "unresolved_blockers": unresolved_items,
        "unresolved_blocker_group_count": len(unresolved_groups),
        "unresolved_blocker_groups": unresolved_groups,
        "output_folder": str(output_dir or ""),
        "packet_name": f"{packet_prefix}_YYYY-MM-DD_HH-MM-SS",
    }


def reconciliation_work_order_rows(readiness):
    rows = []

    def add_row(blocker_type, asset="", year="", date="", source_file="", suspected_issue="", next_action="", status="Open"):
        rows.append({
            "blocker_type": blocker_type,
            "asset": asset,
            "year": year,
            "date": date,
            "source_file": source_file,
            "suspected_issue": suspected_issue,
            "next_action": next_action,
            "status": status,
        })

    for row in readiness.get("missing_records", {}).get("current_holdings", []) or []:
        add_row(
            "Current holdings missing",
            asset=row.get("asset", ""),
            suspected_issue=row.get("message", ""),
            next_action="Enter declared current holdings for this asset.",
        )

    for row in readiness.get("missing_records", {}).get("holdings_explanations", []) or []:
        add_row(
            "Holdings explanation needed",
            asset=row.get("asset", ""),
            suspected_issue=row.get("message", ""),
            next_action="Review transfers, disposals, losses, or missing source files.",
        )

    for row in readiness.get("missing_records", {}).get("basis", []) or []:
        add_row(
            "Missing acquisition basis",
            asset=row.get("asset", ""),
            year=str(row.get("date", ""))[:4],
            date=row.get("date", ""),
            source_file=row.get("source", ""),
            suspected_issue=row.get("message", ""),
            next_action=row.get("note") or "Find earlier acquisition records or leave as needs research with a note.",
            status=row.get("status", "Open"),
        )

    for row in readiness.get("unresolved_import_warning_rows", []) or []:
        add_row(
            "Import warning decision",
            source_file=row.get("source", ""),
            suspected_issue=row.get("issue", "") or row.get("warning", ""),
            next_action=row.get("next_action", "") or "Choose a review decision or add a note.",
        )

    for row in readiness.get("missing_records", {}).get("source_overlaps", []) or []:
        add_row(
            "Possible overlapping source files",
            source_file=", ".join([str(row.get("source_a", "")), str(row.get("source_b", ""))]).strip(", "),
            suspected_issue=row.get("message", ""),
            next_action=row.get("next_action", "Review whether these sources duplicate imported activity."),
            status=row.get("status", "Open"),
        )

    for row in readiness.get("missing_records", {}).get("filed_totals", []) or []:
        add_row(
            "Tax evidence review",
            year=str(row.get("year", "")),
            suspected_issue=row.get("what_gainz_found", "") or row.get("message", ""),
            next_action=row.get("what_gainz_needs", "") or row.get("message", ""),
            status=row.get("status", "Open"),
        )

    if not rows and readiness.get("is_ready"):
        add_row(
            "No open blockers",
            suspected_issue="No unresolved blocker groups are open.",
            next_action="Review generated reports against source records before sharing.",
            status="Ready for review",
        )

    return rows


def reconciliation_work_order_markdown(rows):
    lines = [
        "# Gainz Reconciliation Work Order",
        "",
        "Use this file as a review queue. It is documentation support, not tax, legal, or financial advice.",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend([
            f"## {index}. {row['blocker_type']}",
            "",
            f"- Status: {row['status']}",
            f"- Asset: {row['asset'] or 'N/A'}",
            f"- Year: {row['year'] or 'N/A'}",
            f"- Date: {row['date'] or 'N/A'}",
            f"- Source file: {row['source_file'] or 'N/A'}",
            f"- Suspected issue: {row['suspected_issue'] or 'Review needed.'}",
            f"- Next action: {row['next_action'] or 'Review source records and document the decision.'}",
            "",
        ])
    return "\n".join(lines)
