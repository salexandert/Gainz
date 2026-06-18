import hashlib
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
        "work_order_review_summary": readiness.get("work_order_review_summary", {}),
        "output_folder": str(output_dir or ""),
        "packet_name": f"{packet_prefix}_YYYY-MM-DD_HH-MM-SS",
    }


WORK_ORDER_PRIORITIES = {
    "Missing acquisition basis": (10, "P1 missing acquisition basis"),
    "Reviewed import warning blocker": (20, "P2 reviewed import warning blocker"),
    "Import warning decision": (20, "P2 import warning decision"),
    "Current holdings missing": (30, "P3 holdings explanation gap"),
    "Holdings explanation needed": (30, "P3 holdings explanation gap"),
    "Tax evidence review": (40, "P4 tax evidence review"),
    "Possible overlapping source files": (50, "P5 advisory/documentation item"),
    "No open blockers": (90, "Ready"),
}

WORK_ORDER_REVIEW_DECISIONS = {
    "resolved": "Resolved",
    "needs_research": "Needs research",
    "ignored_for_draft": "Ignored for draft",
    "sent_to_cpa": "Sent to CPA",
}


def work_order_review_choices():
    return [
        {"value": value, "label": label}
        for value, label in WORK_ORDER_REVIEW_DECISIONS.items()
    ]


def work_order_item_id(blocker_type, asset="", year="", date="", source_file="", suspected_issue=""):
    identity = "|".join([
        str(blocker_type or "").strip().lower(),
        str(asset or "").strip().upper(),
        str(year or "").strip(),
        str(date or "").strip(),
        str(source_file or "").strip().lower(),
        str(suspected_issue or "").strip().lower(),
    ])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _work_order_review(transactions, item_id):
    if transactions is None or not hasattr(transactions, "get_work_order_review"):
        return None

    return transactions.get_work_order_review(item_id)


def _apply_work_order_review(row, transactions=None):
    item_id = work_order_item_id(
        row.get("blocker_type", ""),
        asset=row.get("asset", ""),
        year=row.get("year", ""),
        date=row.get("date", ""),
        source_file=row.get("source_file", ""),
        suspected_issue=row.get("suspected_issue", ""),
    )
    review = _work_order_review(transactions, item_id) or {}
    decision = str(review.get("decision") or "").strip()
    decision_label = WORK_ORDER_REVIEW_DECISIONS.get(decision, "")

    row["item_id"] = item_id
    row["review_decision"] = decision
    row["review_decision_label"] = decision_label
    row["review_note"] = review.get("note", "")
    row["review_updated_at"] = review.get("updated_at", "")
    if decision_label:
        row["status"] = decision_label

    return row


def work_order_review_summary(rows):
    actionable_rows = [
        row for row in rows
        if row.get("blocker_type") != "No open blockers"
    ]
    decisions = [row.get("review_decision") for row in actionable_rows]
    reviewed_count = len([decision for decision in decisions if decision])
    summary = {
        "total_items": len(actionable_rows),
        "reviewed_count": reviewed_count,
        "unreviewed_count": len(actionable_rows) - reviewed_count,
        "resolved_count": decisions.count("resolved"),
        "needs_research_count": decisions.count("needs_research"),
        "ignored_for_draft_count": decisions.count("ignored_for_draft"),
        "sent_to_cpa_count": decisions.count("sent_to_cpa"),
    }
    summary["is_complete"] = summary["unreviewed_count"] == 0
    return summary


def reconciliation_work_order_rows(readiness, transactions=None):
    rows = []

    def add_row(blocker_type, asset="", year="", date="", source_file="", suspected_issue="", next_action="", status="Open"):
        priority, priority_label = WORK_ORDER_PRIORITIES.get(
            blocker_type,
            (80, "P5 advisory/documentation item"),
        )
        rows.append({
            "priority": priority,
            "priority_label": priority_label,
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
        has_decision = bool(row.get("decision"))
        decision_label = row.get("decision_label") or row.get("review_status") or "Review needed"
        add_row(
            "Reviewed import warning blocker" if has_decision else "Import warning decision",
            source_file=row.get("source", ""),
            suspected_issue=row.get("issue", "") or row.get("warning", ""),
            next_action=(
                f"Resolve reviewed blocker: {decision_label}. {row.get('next_action', '')}".strip()
                if has_decision
                else row.get("next_action", "") or "Choose a review decision or add a note."
            ),
            status=decision_label if has_decision else "Needs decision",
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

    reviewed_rows = [_apply_work_order_review(row, transactions=transactions) for row in rows]

    return sorted(
        reviewed_rows,
        key=lambda row: (
            int(row.get("priority") or 80),
            str(row.get("year") or ""),
            str(row.get("asset") or ""),
            str(row.get("date") or ""),
            str(row.get("source_file") or ""),
            str(row.get("blocker_type") or ""),
        ),
    )


def reconciliation_work_order_markdown(rows):
    lines = [
        "# Gainz Reconciliation Work Order",
        "",
        "Use this file as a review queue. It is documentation support, not tax, legal, or financial advice.",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend([
            f"## {index}. {row['priority_label']}: {row['blocker_type']}",
            "",
            f"- Item ID: {row.get('item_id') or 'N/A'}",
            f"- Priority: {row['priority']}",
            f"- Status: {row['status']}",
            f"- Review decision: {row.get('review_decision_label') or 'Not reviewed'}",
            f"- Review note: {row.get('review_note') or 'N/A'}",
            f"- Asset: {row['asset'] or 'N/A'}",
            f"- Year: {row['year'] or 'N/A'}",
            f"- Date: {row['date'] or 'N/A'}",
            f"- Source file: {row['source_file'] or 'N/A'}",
            f"- Suspected issue: {row['suspected_issue'] or 'Review needed.'}",
            f"- Next action: {row['next_action'] or 'Review source records and document the decision.'}",
            "",
        ])
    return "\n".join(lines)
