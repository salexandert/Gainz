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
    "import_missing_records": "Import missing records",
    "classify_documented_disposal": "Classify documented send as disposal",
    "keep_owner_transfer": "Keep as owner transfer",
    "document_unknown_basis": "Document unknown basis",
    "needs_research": "Needs research",
    "ignored_for_draft": "Ignore for draft only",
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
    row["cpa_question"] = review.get("cpa_question", "")
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
        "import_missing_records_count": decisions.count("import_missing_records"),
        "classify_documented_disposal_count": decisions.count("classify_documented_disposal"),
        "keep_owner_transfer_count": decisions.count("keep_owner_transfer"),
        "document_unknown_basis_count": decisions.count("document_unknown_basis"),
        "needs_research_count": decisions.count("needs_research"),
        "ignored_for_draft_count": decisions.count("ignored_for_draft"),
        "sent_to_cpa_count": decisions.count("sent_to_cpa"),
    }
    summary["is_complete"] = summary["unreviewed_count"] == 0
    return summary


def _compact_parts(parts):
    return [str(part).strip() for part in parts if str(part or "").strip()]


def _investigator_profile(row):
    blocker_type = row.get("blocker_type", "")
    asset = row.get("asset") or "N/A"
    year = row.get("year") or "N/A"
    date = row.get("date") or "N/A"
    source_file = row.get("source_file") or "N/A"
    issue = row.get("suspected_issue") or "Review needed."

    known = _compact_parts([
        f"Blocker type: {blocker_type}",
        f"Asset: {asset}" if asset != "N/A" else "",
        f"Year/date: {year} / {date}" if year != "N/A" or date != "N/A" else "",
        f"Source file(s): {source_file}" if source_file != "N/A" else "",
        f"Current issue: {issue}",
        f"Current review state: {row.get('review_decision_label') or row.get('status') or 'Not reviewed'}",
    ])

    generic_unknowns = [
        "Whether the current records are complete.",
        "Whether a missing source file, transfer, disposal, or user confirmation explains the gap.",
    ]
    unknowns_by_type = {
        "Missing acquisition basis": [
            "Whether an earlier acquisition record exists before the sale date.",
            "Whether the basis came from another exchange, wallet, income event, fork, airdrop, or prior-year records.",
            "Whether any remaining basis should be documented as unknown for professional review.",
        ],
        "Holdings explanation needed": [
            "Whether the difference is a transfer to a controlled wallet, a disposal, a loss, a gift, or a missing import.",
            "Whether imported sends explain part of the difference.",
            "Whether declared holdings came from a current exchange/wallet balance source.",
        ],
        "Current holdings missing": [
            "What the user currently holds for this asset across exchanges, wallets, and custody accounts.",
            "Whether the asset is intentionally zero or still held somewhere else.",
        ],
        "Import warning decision": [
            "Whether the skipped or assumed row affects holdings, proceeds, cost basis, or evidence review.",
            "Whether the row can be fixed by choosing columns, importing another source file, or adding a manual row.",
        ],
        "Reviewed import warning blocker": [
            "Whether the reviewed warning still needs missing USD value, corrected source data, or professional review.",
        ],
        "Possible overlapping source files": [
            "Whether the files duplicate the same activity or represent different accounts/date ranges.",
            "Which source should remain in the current review data set.",
        ],
        "Tax evidence review": [
            "Whether filed return evidence, payment evidence, crypto workbooks, or user zero-year confirmations exist.",
            "Whether generated totals should be compared with filed totals for this year.",
        ],
    }

    explanations_by_type = {
        "Missing acquisition basis": [
            "Missing acquisition before sale.",
            "Old exchange or wallet export not imported.",
            "Receive/income/fork/airdrop event exists but is not classified with usable basis.",
            "Basis remains unknown and needs documentation.",
        ],
        "Holdings explanation needed": [
            "Imported sends may explain some or all of the holdings gap.",
            "Current holdings suggest a disposal, transfer, loss, gift, or missing source file is not documented yet.",
            "Duplicate or malformed CSV data may be overstating imported activity.",
            "No supporting evidence has resolved the gap yet.",
        ],
        "Current holdings missing": [
            "User has not yet entered current holdings for this asset.",
            "Asset may be zero, held elsewhere, or missing from current balance records.",
        ],
        "Import warning decision": [
            "CSV columns or transaction types may need mapping.",
            "A row may need manual USD value or source-backed manual entry.",
            "The row may be a true zero-value transfer or a non-tax row, but that needs documentation.",
        ],
        "Reviewed import warning blocker": [
            "A review decision was made, but the underlying missing value or assumption still affects packet readiness.",
        ],
        "Possible overlapping source files": [
            "A full-history export and year-specific export may both be imported.",
            "The same activity may appear in two CSVs with different file names.",
        ],
        "Tax evidence review": [
            "Tax evidence exists but filed totals are not confirmed.",
            "Filed return, Form 8949, Schedule D, payment proof, or zero-year confirmation may still be missing.",
        ],
    }

    evidence_by_type = {
        "Missing acquisition basis": [
            "Earlier exchange CSVs or account history before the sale date.",
            "Wallet receive history, 1099s, CPA workbook, or prior tax software export.",
            "Email receipts, purchase confirmations, staking/income reports, fork/airdrop records.",
        ],
        "Holdings explanation needed": [
            "Current wallet/exchange balances for the asset.",
            "Destination wallet or exchange export for sends.",
            "Trade history after sends, withdrawal records, loss/gift documentation, or duplicate-source review.",
        ],
        "Current holdings missing": [
            "Current exchange balances, wallet balances, custody statements, or user confirmation that the asset is zero.",
        ],
        "Import warning decision": [
            "The exact source row, CSV header row, alternate export format, or source-backed manual transaction.",
        ],
        "Reviewed import warning blocker": [
            "Source row with USD value, corrected CSV export, or note explaining why the value remains unresolved.",
        ],
        "Possible overlapping source files": [
            "Date ranges, account names, transaction ids, and row counts for both files.",
        ],
        "Tax evidence review": [
            "Filed return PDF, Form 8949, Schedule D, payment receipt, crypto workbook, tax software export, or zero-year confirmation.",
        ],
    }

    questions_by_type = {
        "Missing acquisition basis": [
            "Do you recognize this exchange, wallet, or asset around the sale date?",
            "Do you remember buying, receiving, earning, or transferring this asset before the sale?",
            "Do you have an older CSV, wallet export, 1099, email receipt, or CPA workbook?",
        ],
        "Holdings explanation needed": [
            "Did you still own this asset after the date range shown?",
            "Could this have moved to a wallet or exchange you controlled?",
            "Was any of this sold, traded, lost, gifted, or included in a prior tax return?",
        ],
        "Current holdings missing": [
            "Do you currently hold this asset anywhere?",
            "If the balance is zero, are you comfortable documenting that as your current declared holdings?",
        ],
        "Import warning decision": [
            "Do you recognize the source file and row?",
            "Does the row belong in your transaction history?",
            "Can you provide a corrected export or manually enter the row with source support?",
        ],
        "Reviewed import warning blocker": [
            "What evidence would confirm the reviewed decision?",
            "Should this be sent to a CPA as unresolved?",
        ],
        "Possible overlapping source files": [
            "Are these two files exports from the same account?",
            "Does one file cover the same date range as the other?",
        ],
        "Tax evidence review": [
            "Was this year filed with crypto activity?",
            "Do you have the filed return, Form 8949, Schedule D, payment proof, or CPA workbook?",
            "Was this year zero or not applicable for crypto?",
        ],
    }

    cpa_questions = {
        "Missing acquisition basis": (
            f"Determine whether {asset} disposal basis can be supported from additional records, "
            "or whether unknown basis needs a documented treatment."
        ),
        "Holdings explanation needed": (
            f"Review the {asset} holdings gap and determine whether documented activity should be treated as transfers, "
            "disposals, gifts, losses, or missing-source indicators."
        ),
        "Current holdings missing": (
            f"Confirm whether current {asset} holdings should be entered as zero, a known current balance, or left for research."
        ),
        "Import warning decision": "Determine whether the import warning affects taxable activity, basis, holdings, or evidence review.",
        "Reviewed import warning blocker": "Review the warning decision and determine what supporting evidence is still needed.",
        "Possible overlapping source files": "Determine whether overlapping source files duplicate activity and which source should remain in the current data set.",
        "Tax evidence review": f"Confirm what filed-return or payment evidence is needed for {year}.",
    }
    why_by_type = {
        "Missing acquisition basis": (
            "Gainz cannot fully support gain/loss for this disposal until earlier acquisition records are found, documented, or intentionally left for professional review."
        ),
        "Reviewed import warning blocker": (
            "A decision was recorded, but the condition still affects generated reports or audit packet readiness."
        ),
        "Import warning decision": (
            "Skipped rows or imported rows with missing values can change holdings, proceeds, basis, or evidence review."
        ),
        "Current holdings missing": (
            "Declared holdings let Gainz compare imported activity against what the user actually holds today."
        ),
        "Holdings explanation needed": (
            "A holdings gap usually means missing transfers, disposals, losses, source files, or classification decisions."
        ),
        "Tax evidence review": (
            "Generated totals are easier to review when filed-return evidence, payment evidence, or user confirmations are recorded by year."
        ),
        "Possible overlapping source files": (
            "Overlapping source files can duplicate activity and make holdings or basis look wrong."
        ),
    }

    return {
        "what_gainz_knows": known,
        "why_it_matters": why_by_type.get(blocker_type, "This item should be documented before treating the packet as complete."),
        "what_gainz_does_not_know": unknowns_by_type.get(blocker_type, generic_unknowns),
        "likely_explanations": explanations_by_type.get(blocker_type, ["No supporting evidence has resolved this item yet."]),
        "evidence_to_look_for": evidence_by_type.get(blocker_type, ["Source records, user notes, or professional review documentation."]),
        "plain_language_questions": questions_by_type.get(blocker_type, ["What do you remember, and what files can support it?"]),
        "allowed_outcomes": [choice["label"] for choice in work_order_review_choices()],
        "suggested_cpa_question": cpa_questions.get(blocker_type, "What should be reviewed before treating this item as complete?"),
    }


def _apply_gap_investigator(row):
    row.update(_investigator_profile(row))
    return row


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

    reviewed_rows = [
        _apply_gap_investigator(_apply_work_order_review(row, transactions=transactions))
        for row in rows
    ]

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


def _list_to_text(values):
    return " | ".join(str(value).strip() for value in values or [] if str(value or "").strip())


def unresolved_gap_memo_rows(rows):
    memo_rows = []
    for row in rows:
        if row.get("blocker_type") == "No open blockers":
            continue
        if row.get("review_decision") == "resolved":
            continue

        cpa_question = row.get("cpa_question") or row.get("suggested_cpa_question") or ""
        memo_rows.append({
            "item_id": row.get("item_id", ""),
            "blocker_type": row.get("blocker_type", ""),
            "asset": row.get("asset", ""),
            "year": row.get("year", ""),
            "date": row.get("date", ""),
            "source_file": row.get("source_file", ""),
            "amount_or_quantity_affected": row.get("suspected_issue", ""),
            "current_decision": row.get("review_decision_label") or "Not reviewed",
            "user_memory_notes": row.get("review_note", ""),
            "cpa_question": cpa_question,
            "what_is_missing": _list_to_text(row.get("what_gainz_does_not_know")),
            "why_it_matters": row.get("why_it_matters", ""),
            "files_checked": row.get("source_file", ""),
            "candidate_explanations": _list_to_text(row.get("likely_explanations")),
            "evidence_to_look_for": _list_to_text(row.get("evidence_to_look_for")),
            "plain_language_questions": _list_to_text(row.get("plain_language_questions")),
            "next_action": row.get("next_action", ""),
        })
    return memo_rows


def unknown_gap_memos_markdown(rows):
    memo_rows = unresolved_gap_memo_rows(rows)
    lines = [
        "# Unknown Gap Memos",
        "",
        "A gap is treated as resolved only when it is explained by evidence, corrected with source data, or explicitly documented for research or CPA review.",
        "These memos preserve uncertainty instead of forcing the user to invent certainty. Gainz is documentation support only, not tax, legal, accounting, or financial advice.",
        "",
    ]

    if not memo_rows:
        lines.extend([
            "No unresolved gap memo items were generated from the current work order.",
            "",
        ])
        return "\n".join(lines)

    for index, row in enumerate(memo_rows, start=1):
        lines.extend([
            f"## {index}. {row['blocker_type']}",
            "",
            f"- Item ID: {row['item_id']}",
            f"- Asset: {row['asset'] or 'N/A'}",
            f"- Year: {row['year'] or 'N/A'}",
            f"- Date: {row['date'] or 'N/A'}",
            f"- Source file(s): {row['source_file'] or 'N/A'}",
            f"- Current decision: {row['current_decision']}",
            f"- Amount/quantity affected: {row['amount_or_quantity_affected'] or 'N/A'}",
            "",
            "### What Is Missing",
            "",
        ])
        lines.extend([f"- {item}" for item in row["what_is_missing"].split(" | ") if item] or ["- N/A"])
        lines.extend(["", "### Candidate Explanations", ""])
        lines.extend([f"- {item}" for item in row["candidate_explanations"].split(" | ") if item] or ["- N/A"])
        lines.extend(["", "### Evidence To Look For", ""])
        lines.extend([f"- {item}" for item in row["evidence_to_look_for"].split(" | ") if item] or ["- N/A"])
        lines.extend([
            "",
            "### User Memory Notes",
            "",
            row["user_memory_notes"] or "No user memory note recorded yet.",
            "",
            "### Suggested CPA Question",
            "",
            row["cpa_question"] or "No CPA question recorded yet.",
            "",
        ])

    return "\n".join(lines)
