import hashlib
import json
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


def packet_review_status(is_ready):
    if is_ready:
        return "Reconciliation complete - professional filing review required"
    return "Draft packet"


def material_assumption_rows(transactions):
    rows = []

    fee_transactions = []
    total_fees = 0.0
    for transaction in getattr(transactions, "transactions", []) or []:
        try:
            fee = float(transaction.prorated_fee_usd(transaction.quantity) or 0.0)
        except (AttributeError, TypeError, ValueError):
            fee = 0.0
        if abs(fee) > 0.0000001:
            fee_transactions.append(transaction)
            total_fees += fee
    if fee_transactions:
        rows.append({
            "category": "Imported fee treatment",
            "title": f"Source fees included for {len(fee_transactions)} transaction(s)",
            "detail": (
                f"Gainz included ${total_fees:.2f} of imported USD fees in proceeds or cost basis. "
                "Review 01_reports/import_economics.csv for source gross, fee, and net values."
            ),
            "status": "Calculation input",
        })

    seen_warnings = set()
    for transaction in getattr(transactions, "transactions", []) or []:
        warning = str(getattr(transaction, "economics_warning", "") or "").strip()
        if not warning or warning in seen_warnings:
            continue
        seen_warnings.add(warning)
        rows.append({
            "category": "Imported economics warning",
            "title": warning,
            "detail": (
                f"Source: {Path(str(getattr(transaction, 'source', '') or 'Unknown')).name}; "
                f"asset: {getattr(transaction, 'symbol', '') or 'Unknown'}."
            ),
            "status": "Needs review",
        })

    for review in getattr(transactions, "work_order_reviews", []) or []:
        if str(review.get("calculation_applied") or "") != "Yes":
            continue
        receipt = {}
        try:
            receipt = json.loads(str(review.get("calculation_receipt_json") or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            receipt = {}
        asset = str(review.get("asset") or receipt.get("asset") or "Asset")
        basis_method = CPA_BASIS_METHODS.get(
            str(review.get("basis_method") or ""),
            str(review.get("basis_method") or "Not recorded"),
        )
        date_method = CPA_ACQUISITION_DATE_METHODS.get(
            str(review.get("acquisition_date_method") or ""),
            str(review.get("acquisition_date_method") or "Not recorded"),
        )
        rows.append({
            "category": "Professional calculation treatment",
            "title": f"{asset} treatment applied under direction recorded by the user",
            "detail": (
                f"Basis: {basis_method}; holding period: {date_method}; "
                f"added proceeds ${float(receipt.get('added_proceeds') or 0):.2f}; "
                f"added basis ${float(receipt.get('added_basis') or 0):.2f}; "
                f"gain/loss effect ${float(receipt.get('added_gain_loss') or 0):.2f}. "
                f"Evidence: {review.get('evidence_reference') or 'Not recorded'}."
            ),
            "status": "Applied - reversible",
        })

    return rows


def get_packet_preview(transactions, readiness, output_dir):
    source_paths = transaction_source_paths(transactions)
    evidence_counts = tax_evidence_packet_counts(transactions)
    is_ready = bool(readiness.get("is_ready"))
    packet_prefix = "gainz_audit_packet" if is_ready else "gainz_audit_packet_DRAFT"
    unresolved_items = list(readiness.get("blockers") or []) + list(readiness.get("warnings") or [])
    unresolved_groups = list(readiness.get("blocker_groups") or [])

    assumptions = material_assumption_rows(transactions)

    return {
        "status": packet_review_status(is_ready),
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
        "material_assumption_count": len(assumptions),
        "material_assumptions": assumptions,
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
    "fork_airdrop_basis": "Fork/airdrop acquisition",
    "already_in_filed_totals": "Already included in filed tax totals",
    "zero_basis_cpa_review": "Treat unknown basis as $0 for CPA review",
    "conservative_max_gain": "Apply conservative $0-basis short-term treatment",
    "needs_research": "Needs research",
    "ignored_for_draft": "Leave unresolved for draft only",
    "sent_to_cpa": "Sent to CPA",
}

CPA_REVIEWER_ROLES = {
    "": "Not recorded",
    "taxpayer": "Taxpayer",
    "cpa_ea_tax_professional": "CPA, EA, or tax professional",
    "other_reviewer": "Other reviewer",
}

CPA_EVENT_CLASSIFICATIONS = {
    "": "Not determined",
    "owner_transfer": "Transfer between accounts under the same ownership",
    "cash_sale": "Sale for cash",
    "crypto_exchange": "Exchange for another digital asset",
    "goods_or_services": "Payment for goods or services",
    "gift_or_donation": "Gift or donation",
    "fee": "Digital asset used to pay a fee",
    "other_disposition": "Other documented disposition",
    "conservative_unknown_disposition": "Unresolved event treated as a taxable disposition for conservative review",
    "unknown": "Unknown event",
}

CPA_PROCEEDS_METHODS = {
    "": "Not determined",
    "source_reported": "Amount reported by source record or broker form",
    "allocated_source_value": "Calculated allocation from imported source transaction",
    "disposition_date_fmv": "Fair market value at disposition",
    "property_received_fmv": "Fair market value of property or services received",
    "filed_form": "Amount reported on filed Form 8949 or Schedule D",
    "manual_supported": "Other supported professional determination",
    "not_applicable": "Not applicable",
    "unknown": "Unknown proceeds",
}

CPA_BASIS_METHODS = {
    "": "Not determined",
    "imported_fifo": "Linked acquisition records using FIFO",
    "specific_identification": "Specific identification supported by records",
    "documented_acquisition_cost": "Documented acquisition cost",
    "income_fmv_when_received": "FMV when received as income",
    "fork_airdrop_supported": "Fork or airdrop basis supported by records",
    "carryover_basis": "Supported carryover basis",
    "actual_zero_basis": "Asset actually had a zero basis",
    "unknown_zero_for_review": "Conservative $0 basis under recorded professional direction",
    "unknown": "Unknown basis",
    "not_applicable": "Not applicable",
}

CPA_RESOLUTION_STATUSES = {
    "": "Not set",
    "draft_research": "Draft - needs research",
    "prepared_for_cpa": "Prepared for CPA review",
    "cpa_reviewed_position": "Professional direction recorded by user",
    "previously_filed": "Previously filed treatment",
}

CPA_ACQUISITION_DATE_METHODS = {
    "": "Not determined",
    "documented_date": "Documented acquisition date",
    "cpa_conservative_short_term": "Unknown date - recorded short-term assumption",
}

CONSERVATIVE_MAX_GAIN_DISCLOSURE = (
    "Gainz could not reconstruct the acquisition history for this exact quantity. The user recorded "
    "professional direction to use supported proceeds, $0 adjusted basis, and a "
    "short-term holding-period assumption for its capital-gain calculation. The acquisition date "
    "remains unknown and is left blank in report rows. This treatment may overstate tax and does "
    "not establish what actually happened. Gainz does not verify the reviewer's identity or credentials."
)


def cpa_resolution_choices():
    def options(values):
        return [
            {"value": value, "label": label}
            for value, label in values.items()
        ]

    return {
        "reviewer_roles": options(CPA_REVIEWER_ROLES),
        "event_classifications": options(CPA_EVENT_CLASSIFICATIONS),
        "proceeds_methods": options(CPA_PROCEEDS_METHODS),
        "basis_methods": options(CPA_BASIS_METHODS),
        "resolution_statuses": options(CPA_RESOLUTION_STATUSES),
        "acquisition_date_methods": options(CPA_ACQUISITION_DATE_METHODS),
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
    item_id = row.get("item_id") or work_order_item_id(
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
    row["reviewer_name"] = review.get("reviewer_name", "")
    row["reviewer_role"] = review.get("reviewer_role", "")
    row["reviewer_role_label"] = CPA_REVIEWER_ROLES.get(row["reviewer_role"], "")
    row["direction_date"] = review.get("direction_date", "")
    row["direction_entered_by"] = review.get("direction_entered_by", "")
    row["reviewer_credential"] = review.get("reviewer_credential", "")
    row["reviewer_jurisdiction"] = review.get("reviewer_jurisdiction", "")
    row["event_classification"] = review.get("event_classification", "")
    row["event_classification_label"] = CPA_EVENT_CLASSIFICATIONS.get(
        row["event_classification"],
        "",
    )
    row["proceeds_method"] = review.get("proceeds_method", "")
    row["proceeds_method_label"] = CPA_PROCEEDS_METHODS.get(row["proceeds_method"], "")
    row["proceeds_value"] = review.get("proceeds_value", "")
    row["basis_method"] = review.get("basis_method", "")
    row["basis_method_label"] = CPA_BASIS_METHODS.get(row["basis_method"], "")
    row["basis_value"] = review.get("basis_value", "")
    row["acquisition_date_method"] = review.get("acquisition_date_method", "")
    row["acquisition_date_method_label"] = CPA_ACQUISITION_DATE_METHODS.get(
        row["acquisition_date_method"],
        "",
    )
    row["assumption_disclosure"] = review.get("assumption_disclosure", "")
    row["evidence_reference"] = review.get("evidence_reference", "")
    row["resolution_status"] = review.get("resolution_status", "")
    row["resolution_status_label"] = CPA_RESOLUTION_STATUSES.get(row["resolution_status"], "")
    row["professional_attestation"] = review.get("professional_attestation", "")
    for field in (
        "blocker_type",
        "asset",
        "year",
        "date",
        "quantity",
        "transaction_quantity",
        "source_file",
        "suspected_issue",
        "target_transaction_uid",
    ):
        row[field] = review.get(field) or row.get(field, "")
    row["acquisition_date"] = review.get("acquisition_date", "")
    row["calculation_applied"] = review.get("calculation_applied", "")
    row["adjustment_transaction_uid"] = review.get("adjustment_transaction_uid", "")
    row["calculation_receipt_json"] = review.get("calculation_receipt_json", "")
    row["resolution_applied_at"] = review.get("resolution_applied_at", "")
    row["resolution_reversed_at"] = review.get("resolution_reversed_at", "")
    row["reversal_note"] = review.get("reversal_note", "")
    row["has_cpa_resolution_details"] = any([
        row["reviewer_name"],
        row["reviewer_role"],
        row["direction_date"],
        row["direction_entered_by"],
        row["reviewer_credential"],
        row["reviewer_jurisdiction"],
        row["event_classification"],
        row["proceeds_method"],
        row["proceeds_value"],
        row["basis_method"],
        row["basis_value"],
        row["acquisition_date_method"],
        row["assumption_disclosure"],
        row["evidence_reference"],
        row["resolution_status"],
        row["professional_attestation"],
        row["acquisition_date"],
        row["calculation_applied"],
        row["calculation_receipt_json"],
    ])
    row["review_updated_at"] = review.get("updated_at", "")
    if decision_label:
        row["status"] = decision_label

    return row


def cpa_resolution_workpaper_rows(readiness, transactions):
    current_rows = {
        row.get("item_id"): row
        for row in reconciliation_work_order_rows(readiness, transactions)
        if row.get("item_id")
    }
    rows = []
    for review in getattr(transactions, "work_order_reviews", []) or []:
        item_id = str(review.get("item_id") or "")
        context = dict(current_rows.get(item_id) or {
            "item_id": item_id,
            "blocker_type": review.get("blocker_type", ""),
            "asset": review.get("asset", ""),
            "year": review.get("year", ""),
            "date": review.get("date", ""),
            "quantity": review.get("quantity", ""),
            "transaction_quantity": review.get("transaction_quantity", ""),
            "source_file": review.get("source_file", ""),
            "suspected_issue": review.get("suspected_issue", ""),
            "target_transaction_uid": review.get("target_transaction_uid", ""),
            "status": "Applied resolution" if review.get("calculation_applied") else "Documented review",
        })
        row = _apply_work_order_review(context, transactions)
        if row.get("has_cpa_resolution_details"):
            rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            str(row.get("year") or ""),
            str(row.get("asset") or ""),
            str(row.get("date") or ""),
            str(row.get("item_id") or ""),
        ),
    )


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
        "fork_airdrop_basis_count": decisions.count("fork_airdrop_basis"),
        "already_in_filed_totals_count": decisions.count("already_in_filed_totals"),
        "zero_basis_cpa_review_count": decisions.count("zero_basis_cpa_review"),
        "conservative_max_gain_count": decisions.count("conservative_max_gain"),
        "needs_research_count": decisions.count("needs_research"),
        "ignored_for_draft_count": decisions.count("ignored_for_draft"),
        "sent_to_cpa_count": decisions.count("sent_to_cpa"),
        "cpa_documented_count": len([
            row for row in actionable_rows
            if row.get("has_cpa_resolution_details")
        ]),
        "cpa_reviewed_position_count": len([
            row for row in actionable_rows
            if row.get("resolution_status") == "cpa_reviewed_position"
        ]),
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

    def add_row(
        blocker_type,
        asset="",
        year="",
        date="",
        quantity="",
        transaction_quantity="",
        target_transaction_uid="",
        source_file="",
        suspected_issue="",
        next_action="",
        status="Open",
    ):
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
            "quantity": quantity,
            "transaction_quantity": transaction_quantity,
            "target_transaction_uid": target_transaction_uid,
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
            quantity=row.get("unlinked_quantity", ""),
            transaction_quantity=row.get("quantity", ""),
            target_transaction_uid=row.get("target_transaction_uid", ""),
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
            f"- Reviewer: {row.get('reviewer_name') or 'N/A'} ({row.get('reviewer_role_label') or 'role not recorded'})",
            f"- Direction date: {row.get('direction_date') or 'N/A'}",
            f"- Direction entered by: {row.get('direction_entered_by') or 'N/A'}",
            f"- Credential entered by user: {row.get('reviewer_credential') or 'Not recorded'}",
            f"- Jurisdiction entered by user: {row.get('reviewer_jurisdiction') or 'Not recorded'}",
            f"- Resolution status: {row.get('resolution_status_label') or 'Not set'}",
            f"- Asset: {row['asset'] or 'N/A'}",
            f"- Year: {row['year'] or 'N/A'}",
            f"- Date: {row['date'] or 'N/A'}",
            f"- Quantity under review: {row.get('quantity') or 'N/A'}",
            f"- Source file: {row['source_file'] or 'N/A'}",
            f"- Event classification: {row.get('event_classification_label') or 'Not determined'}",
            f"- Proceeds method: {row.get('proceeds_method_label') or 'Not determined'}",
            f"- Proceeds value: {row.get('proceeds_value') or 'N/A'}",
            f"- Basis method: {row.get('basis_method_label') or 'Not determined'}",
            f"- Basis value: {row.get('basis_value') or 'N/A'}",
            f"- Acquisition-date method: {row.get('acquisition_date_method_label') or 'Not determined'}",
            f"- Acquisition date: {row.get('acquisition_date') or 'N/A'}",
            f"- Conservative assumption disclosure: {row.get('assumption_disclosure') or 'N/A'}",
            f"- Evidence reference: {row.get('evidence_reference') or 'N/A'}",
            f"- Applied to calculations: {row.get('calculation_applied') or 'No'}",
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
        if row.get("review_decision") == "resolved" or row.get("calculation_applied"):
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
            "resolution_status": row.get("resolution_status_label") or "Not set",
            "reviewer": " / ".join(_compact_parts([
                row.get("reviewer_name"),
                row.get("reviewer_role_label"),
            ])),
            "event_classification": row.get("event_classification_label") or "Not determined",
            "proceeds_method": row.get("proceeds_method_label") or "Not determined",
            "proceeds_value": row.get("proceeds_value", ""),
            "basis_method": row.get("basis_method_label") or "Not determined",
            "basis_value": row.get("basis_value", ""),
            "evidence_reference": row.get("evidence_reference", ""),
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
            f"- Resolution status: {row['resolution_status']}",
            f"- Reviewer: {row['reviewer'] or 'N/A'}",
            f"- Event classification: {row['event_classification']}",
            f"- Proceeds method/value: {row['proceeds_method']} / {row['proceeds_value'] or 'N/A'}",
            f"- Basis method/value: {row['basis_method']} / {row['basis_value'] or 'N/A'}",
            f"- Evidence reference: {row['evidence_reference'] or 'N/A'}",
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
