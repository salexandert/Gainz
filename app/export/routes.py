import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import blueprint
from flask import render_template, request, jsonify, current_app, redirect, session, url_for
from flask_login import current_user, login_required
from utils import *
from app.services.export_service import ExportService
from app.services.audit_packet_service import AuditPacketService
from app.services.packet_plan_service import (
    CONSERVATIVE_MAX_GAIN_DISCLOSURE,
    CPA_ACQUISITION_DATE_METHODS,
    CPA_BASIS_METHODS,
    CPA_EVENT_CLASSIFICATIONS,
    CPA_PROCEEDS_METHODS,
    CPA_RESOLUTION_STATUSES,
    CPA_REVIEWER_ROLES,
    WORK_ORDER_REVIEW_DECISIONS,
    cpa_resolution_choices,
    get_packet_preview,
    packet_review_status,
    reconciliation_work_order_rows,
    work_order_review_choices,
)


def _path_for_display(path):
    return str(Path(path).expanduser().resolve())


def _detected_tax_folder():
    candidate = Path.home() / "OneDrive" / "Taxes"
    return str(candidate) if candidate.exists() and candidate.is_dir() else ""


def _default_packet_output_folder():
    return _detected_tax_folder() or current_app.config['AUDIT_PACKET_FOLDER']


def _output_location_choices():
    choices = {
        "audit_packets": current_app.config['AUDIT_PACKET_FOLDER'],
        "exports": current_app.config['EXPORT_FOLDER'],
    }
    detected_tax_folder = _detected_tax_folder()
    if detected_tax_folder:
        choices["detected_taxes"] = detected_tax_folder
    return choices


def _output_location_key():
    payload = request.get_json(silent=True) or {}
    return str(
        payload.get("output_location")
        or request.args.get("output_location")
        or request.form.get("output_location")
        or ""
    ).strip()


def _output_dir_for_location(default_folder, create=False):
    choices = _output_location_choices()
    location_key = _output_location_key()
    folder = choices.get(location_key) or default_folder
    output_dir = Path(folder).expanduser()

    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError("Output location must be a folder, not a file.")

    if create:
        output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir.resolve()


def _truthy_payload_value(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _optional_money(value, label):
    text = str(value or "").strip().replace("$", "").replace(",", "")
    if not text:
        return "", ""

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return "", f"Enter a valid {label} in U.S. dollars."

    if not amount.is_finite():
        return "", f"Enter a finite {label} in U.S. dollars."

    if amount < 0:
        return "", f"{label.capitalize()} cannot be negative."

    return f"{amount:.2f}", ""


def _cpa_resolution_details(source):
    entered_by = str(getattr(current_user, "username", "") or "").strip()
    proceeds_value, proceeds_error = _optional_money(
        source.get("proceeds_value"),
        "proceeds or amount realized for the unresolved quantity",
    )
    basis_value, basis_error = _optional_money(
        source.get("basis_value"),
        "total adjusted basis",
    )
    error = proceeds_error or basis_error

    details = {
        "reviewer_name": str(source.get("reviewer_name") or "").strip(),
        "reviewer_role": str(source.get("reviewer_role") or "").strip(),
        "direction_date": str(source.get("direction_date") or datetime.date.today().isoformat()).strip(),
        "direction_entered_by": str(
            source.get("direction_entered_by") or entered_by or "Local Gainz user"
        ).strip(),
        "reviewer_credential": str(source.get("reviewer_credential") or "").strip(),
        "reviewer_jurisdiction": str(source.get("reviewer_jurisdiction") or "").strip(),
        "event_classification": str(source.get("event_classification") or "").strip(),
        "proceeds_method": str(source.get("proceeds_method") or "").strip(),
        "proceeds_value": proceeds_value,
        "basis_method": str(source.get("basis_method") or "").strip(),
        "basis_value": basis_value,
        "evidence_reference": str(source.get("evidence_reference") or "").strip(),
        "resolution_status": str(source.get("resolution_status") or "").strip(),
        "acquisition_date_method": str(source.get("acquisition_date_method") or "").strip(),
        "acquisition_date": str(source.get("acquisition_date") or "").strip(),
        "assumption_disclosure": str(source.get("assumption_disclosure") or "").strip(),
        "professional_attestation": (
            "Yes" if _truthy_payload_value(source.get("professional_attestation")) else ""
        ),
    }
    return details, error


def _validate_cpa_resolution(item, decision, details, note="", for_preview=False):
    choice_sets = (
        ("reviewer_role", CPA_REVIEWER_ROLES, "reviewer role"),
        ("event_classification", CPA_EVENT_CLASSIFICATIONS, "event classification"),
        ("proceeds_method", CPA_PROCEEDS_METHODS, "proceeds method"),
        ("basis_method", CPA_BASIS_METHODS, "basis method"),
        ("resolution_status", CPA_RESOLUTION_STATUSES, "resolution status"),
        ("acquisition_date_method", CPA_ACQUISITION_DATE_METHODS, "acquisition-date method"),
    )
    for field, allowed, label in choice_sets:
        if details[field] not in allowed:
            return f"Choose a valid {label}."

    if decision == "keep_owner_transfer":
        details["event_classification"] = "owner_transfer"
        details["proceeds_method"] = details["proceeds_method"] or "not_applicable"
        details["basis_method"] = details["basis_method"] or "not_applicable"
        if not details["evidence_reference"] and not note:
            return "Add the wallet/account evidence or a note supporting the owner-transfer decision."

    if decision == "classify_documented_disposal":
        if details["event_classification"] in {"", "unknown", "owner_transfer"}:
            return "Choose the documented sale, exchange, payment, fee, gift, or other disposition type."
        if details["proceeds_method"] in {"", "unknown", "not_applicable"}:
            return "Choose how proceeds or amount realized for the unresolved quantity were determined."
        if not details["proceeds_value"]:
            return "Enter supported proceeds or amount realized for the unresolved quantity in U.S. dollars."
        if not details["evidence_reference"] and not note:
            return "Cite the source record, valuation source, workpaper, or other evidence for this disposition."
        details["resolution_status"] = details["resolution_status"] or "prepared_for_cpa"

    if decision == "zero_basis_cpa_review":
        if details["event_classification"] in {"", "unknown", "owner_transfer"}:
            return "Confirm the documented disposition type before considering an unknown-basis treatment."
        if details["proceeds_method"] in {"", "unknown", "not_applicable"}:
            return "Choose how proceeds or amount realized for the unresolved quantity were determined."
        if not details["proceeds_value"]:
            return "Enter supported proceeds or amount realized for the unresolved quantity in U.S. dollars."
        if not details["evidence_reference"] and not note:
            return "Cite the records supporting the disposition and valuation."
        details["basis_method"] = "unknown_zero_for_review"
        details["basis_value"] = "0.00"
        details["resolution_status"] = "prepared_for_cpa"

    if decision == "conservative_max_gain":
        if item.get("blocker_type") != "Missing acquisition basis":
            return "Conservative $0-basis short-term treatment is available only for an identified sale with missing basis."
        if details["event_classification"] in {"", "unknown", "owner_transfer"}:
            details["event_classification"] = "conservative_unknown_disposition"
        if details["proceeds_method"] in {"", "unknown", "not_applicable"}:
            return "Choose how supported proceeds or amount realized were determined."
        if not details["proceeds_value"]:
            return "Enter supported proceeds or amount realized for the unresolved quantity in U.S. dollars."
        if not details["evidence_reference"] and not note:
            return "Cite the records checked, valuation source, and professional workpaper supporting this assumption."
        details["basis_method"] = "unknown_zero_for_review"
        details["basis_value"] = "0.00"
        details["acquisition_date_method"] = "cpa_conservative_short_term"
        details["acquisition_date"] = ""
        details["assumption_disclosure"] = CONSERVATIVE_MAX_GAIN_DISCLOSURE
        details["resolution_status"] = "cpa_reviewed_position"

    if decision == "fork_airdrop_basis":
        details["basis_method"] = details["basis_method"] or "fork_airdrop_supported"
        if not details["evidence_reference"] and not note:
            return "Cite the fork, airdrop, income, or acquisition evidence supporting this treatment."

    if decision == "already_in_filed_totals":
        details["resolution_status"] = details["resolution_status"] or "previously_filed"
        if not details["evidence_reference"]:
            return "Cite the filed Form 8949, Schedule D, return, or CPA workpaper."

    if decision in {"needs_research", "ignored_for_draft"}:
        details["resolution_status"] = details["resolution_status"] or "draft_research"

    if decision == "sent_to_cpa":
        details["resolution_status"] = details["resolution_status"] or "prepared_for_cpa"

    if details["resolution_status"] == "cpa_reviewed_position":
        if details["reviewer_role"] != "cpa_ea_tax_professional":
            return "Recorded professional direction requires the CPA, EA, or tax professional reviewer role."
        if not details["reviewer_name"]:
            return "Enter the reviewing professional's name."
        if not details["professional_attestation"]:
            return "Confirm that you are recording the named professional's direction."
        if not details["direction_date"]:
            return "Enter the date of the professional direction."
        try:
            datetime.date.fromisoformat(details["direction_date"])
        except ValueError:
            return "Enter a valid professional direction date."
        if not details["direction_entered_by"]:
            return "Record who entered the professional direction into Gainz."
        if not details["evidence_reference"]:
            return "Cite the evidence or workpaper supporting the filing position."
        if details["event_classification"] in {"", "unknown"}:
            return "Choose the event classification supporting the filing position."
        if details["event_classification"] not in {"owner_transfer", "gift_or_donation"}:
            if details["proceeds_method"] in {"", "unknown", "not_applicable"} or not details["proceeds_value"]:
                return "Record supported proceeds or amount realized for this filing position."
            if details["basis_method"] in {"", "unknown", "not_applicable"}:
                return "Record the CPA-approved adjusted-basis method."
            if details["basis_method"] != "actual_zero_basis" and not details["basis_value"]:
                if details["basis_method"] != "unknown_zero_for_review":
                    return "Enter the supported total adjusted basis."

    if decision in {"resolved", "conservative_max_gain"} and item.get("blocker_type") == "Missing acquisition basis":
        if not for_preview and details["resolution_status"] != "cpa_reviewed_position":
            return "Choose Professional direction recorded by user before applying this resolution to calculations."
        if details["event_classification"] not in {
            "cash_sale",
            "crypto_exchange",
            "goods_or_services",
            "fee",
            "other_disposition",
            "conservative_unknown_disposition",
        }:
            return "Choose the documented taxable disposition type for this sale."
        if details["basis_method"] in {
            "",
            "unknown",
            "not_applicable",
            "imported_fifo",
            "specific_identification",
        }:
            return (
                "Choose the professionally directed basis adjustment method. Import or link actual lots instead "
                "when using FIFO or specific identification."
            )
        if details["basis_method"] in {"actual_zero_basis", "unknown_zero_for_review"}:
            details["basis_value"] = "0.00"
        elif not details["basis_value"]:
            return "Enter the adjusted basis for the unresolved quantity."
        if details["acquisition_date_method"] == "cpa_conservative_short_term":
            if details["basis_method"] != "unknown_zero_for_review" or details["basis_value"] != "0.00":
                return "The conservative short-term assumption must use the recorded $0-basis method."
            if not details["assumption_disclosure"]:
                details["assumption_disclosure"] = CONSERVATIVE_MAX_GAIN_DISCLOSURE
        else:
            details["acquisition_date_method"] = "documented_date"
            if not details["acquisition_date"]:
                return "Enter the supported acquisition date used for Form 8949 reporting."
            try:
                datetime.date.fromisoformat(details["acquisition_date"])
            except ValueError:
                return "Enter a valid acquisition date."
        if not item.get("target_transaction_uid"):
            return "Gainz cannot identify the exact sale row. Refresh the review queue before applying the resolution."

    return ""


def _work_order_context_fields(item):
    return {
        field: item.get(field, "")
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
        )
    }


def _resolution_impact_preview(transactions, item, decision, details):
    totals_before = get_form_8949_totals(transactions)["total"]
    changes_calculations = (
        decision in {"resolved", "conservative_max_gain"}
        and item.get("blocker_type") == "Missing acquisition basis"
    )
    proceeds = float(details.get("proceeds_value") or 0.0)
    basis = float(details.get("basis_value") or 0.0)
    gain_loss = proceeds - basis
    target_sell = next(
        (
            transaction
            for transaction in transactions
            if transaction.uid == item.get("target_transaction_uid")
            and transaction.trans_type == "sell"
        ),
        None,
    )
    source_fee = 0.0
    source_gross = 0.0
    source_net = 0.0
    if target_sell is not None:
        quantity = float(item.get("quantity") or 0.0)
        source_fee = target_sell.prorated_fee_usd(quantity)
        source_gross = target_sell.prorated_gross_usd(quantity)
        source_net = target_sell.prorated_tax_usd(quantity)

    added_proceeds = proceeds if changes_calculations else 0.0
    added_basis = basis if changes_calculations else 0.0
    added_gain_loss = gain_loss if changes_calculations else 0.0
    return {
        "changes_calculations": changes_calculations,
        "decision": decision,
        "decision_label": WORK_ORDER_REVIEW_DECISIONS.get(decision, decision),
        "asset": item.get("asset", ""),
        "quantity": item.get("quantity", ""),
        "source_file": item.get("source_file", ""),
        "source_gross": source_gross,
        "source_fee": source_fee,
        "source_net": source_net,
        "added_proceeds": added_proceeds,
        "added_basis": added_basis,
        "added_gain_loss": added_gain_loss,
        "before_proceeds": totals_before["proceeds"],
        "before_basis": totals_before["cost_basis"],
        "before_gain_loss": totals_before["gain_loss"],
        "after_proceeds": totals_before["proceeds"] + added_proceeds,
        "after_basis": totals_before["cost_basis"] + added_basis,
        "after_gain_loss": totals_before["gain_loss"] + added_gain_loss,
        "term": (
            "Short-term assumption"
            if details.get("acquisition_date_method") == "cpa_conservative_short_term"
            else "Based on recorded acquisition date"
        ),
        "assumption_disclosure": details.get("assumption_disclosure", ""),
        "evidence_reference": details.get("evidence_reference", ""),
        "reviewer_name": details.get("reviewer_name", ""),
        "direction_date": details.get("direction_date", ""),
        "direction_entered_by": details.get("direction_entered_by", ""),
        "reviewer_credential": details.get("reviewer_credential", ""),
        "reviewer_jurisdiction": details.get("reviewer_jurisdiction", ""),
        "credential_notice": (
            "Professional name, role, credential, jurisdiction, and direction are entered by the user. Gainz does not verify them."
        ),
    }


def _resolution_preview_fingerprint(item, decision, details, note="", cpa_question=""):
    payload = {
        "item_id": str(item.get("item_id") or ""),
        "target_transaction_uid": str(item.get("target_transaction_uid") or ""),
        "quantity": str(item.get("quantity") or ""),
        "decision": str(decision or ""),
        "details": {key: str(value or "") for key, value in sorted(details.items())},
        "note": str(note or ""),
        "cpa_question": str(cpa_question or ""),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _resolution_form_context(transactions, item_id, decision, details=None, note="", cpa_question=""):
    context = _review_queue_context(transactions, item_id=item_id)
    context["selected_decision"] = decision
    context["selected_decision_label"] = WORK_ORDER_REVIEW_DECISIONS.get(decision, decision)
    if context.get("item") is None:
        return context

    item = context["item"]
    for field, value in (details or {}).items():
        if value not in (None, ""):
            item[field] = value
    item["review_note"] = note
    item["cpa_question"] = cpa_question

    if decision == "conservative_max_gain":
        item["event_classification"] = "conservative_unknown_disposition"
        item["basis_method"] = "unknown_zero_for_review"
        item["basis_value"] = "0.00"
        item["acquisition_date_method"] = "cpa_conservative_short_term"
        item["acquisition_date"] = ""
        item["assumption_disclosure"] = CONSERVATIVE_MAX_GAIN_DISCLOSURE
        item["resolution_status"] = "cpa_reviewed_position"
    elif decision == "zero_basis_cpa_review":
        item["basis_method"] = "unknown_zero_for_review"
        item["basis_value"] = "0.00"
        item["resolution_status"] = "prepared_for_cpa"
    elif decision == "fork_airdrop_basis":
        item["basis_method"] = item.get("basis_method") or "fork_airdrop_supported"
    elif decision == "already_in_filed_totals":
        item["resolution_status"] = item.get("resolution_status") or "previously_filed"
    elif decision in {"needs_research", "ignored_for_draft"}:
        item["resolution_status"] = item.get("resolution_status") or "draft_research"
    elif decision == "sent_to_cpa":
        item["resolution_status"] = item.get("resolution_status") or "prepared_for_cpa"

    return context


def _apply_cpa_calculation_resolution(transactions, item, item_id, decision, details):
    if decision not in {"resolved", "conservative_max_gain"} or item.get("blocker_type") != "Missing acquisition basis":
        return ""

    receipt_before = _resolution_impact_preview(transactions, item, decision, details)
    try:
        adjustment_buy, _link = transactions.apply_cpa_basis_resolution(
            target_sell_uid=item.get("target_transaction_uid"),
            quantity=item.get("quantity"),
            acquisition_date=details.get("acquisition_date"),
            basis_value=details.get("basis_value"),
            proceeds_value=details.get("proceeds_value"),
            basis_method=CPA_BASIS_METHODS.get(details.get("basis_method"), details.get("basis_method")),
            evidence_reference=details.get("evidence_reference"),
            work_order_item_id=item_id,
            acquisition_date_method=details.get("acquisition_date_method") or "documented_date",
        )
    except (TypeError, ValueError):
        current_app.logger.exception("CPA calculation resolution could not be applied")
        return (
            "Gainz could not apply this professional resolution. Check the selected sale, "
            "unresolved quantity, acquisition date, and USD values, then try again."
        )

    details["calculation_applied"] = "Yes"
    details["adjustment_transaction_uid"] = adjustment_buy.uid
    receipt_after = _resolution_impact_preview(transactions, item, decision, details)
    receipt = dict(receipt_before)
    receipt["actual_after_proceeds"] = receipt_after["before_proceeds"]
    receipt["actual_after_basis"] = receipt_after["before_basis"]
    receipt["actual_after_gain_loss"] = receipt_after["before_gain_loss"]
    details["calculation_receipt_json"] = json.dumps(receipt, sort_keys=True)
    details["resolution_applied_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details["resolution_reversed_at"] = ""
    details["reversal_note"] = ""
    return ""


def _draft_acknowledged():
    payload = request.get_json(silent=True) or {}
    return _truthy_payload_value(payload.get("draft_acknowledged") or request.form.get("draft_acknowledged"))


def _guided_requested():
    payload = request.get_json(silent=True) or {}
    return _truthy_payload_value(
        payload.get("guided")
        or request.form.get("guided")
        or request.args.get("guided")
    )


def _draft_ack_error(transactions, output_label):
    readiness = get_audit_readiness_summary(transactions)
    if readiness["is_ready"] or _draft_acknowledged():
        return None

    return jsonify({
        "message": (
            f"{output_label} is draft-only because Gainz still has unresolved review items. "
            "Check the draft acknowledgement before generating files."
        ),
        "status": readiness["status"],
        "requires_draft_acknowledgement": True,
    }), 400


def _draft_workbook_path(path):
    path = Path(path)
    if path.name.startswith("DRAFT_"):
        return str(path)

    candidate = path.with_name(f"DRAFT_{path.name}")
    if not candidate.exists():
        path.replace(candidate)
        return str(candidate)

    index = 2
    while True:
        candidate = path.with_name(f"DRAFT_{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            path.replace(candidate)
            return str(candidate)
        index += 1


def _open_existing_local_path(path):
    path = Path(path).resolve()
    if not path.exists():
        return False

    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])
    return True


def _last_packet_path():
    value = session.get("last_packet_path") or ""
    if not value:
        return None

    packet_path = Path(value).resolve()
    if packet_path.exists() and packet_path.is_dir():
        return packet_path

    return None


def _work_order_rows(transactions):
    readiness = get_audit_readiness_summary(transactions)
    return [
        row for row in reconciliation_work_order_rows(readiness, transactions)
        if row.get("blocker_type") != "No open blockers"
    ]


def _work_order_why_it_matters(row):
    blocker_type = row.get("blocker_type")
    return {
        "Missing acquisition basis": (
            "Gainz cannot fully support gain/loss for this disposal until earlier acquisition "
            "records are found, documented, or intentionally left for professional review."
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
    }.get(blocker_type, "This item should be documented before treating the packet as complete.")


def _work_order_related_url(row):
    blocker_type = row.get("blocker_type")
    if blocker_type in {"Current holdings missing", "Holdings explanation needed", "Missing acquisition basis"}:
        return url_for(
            "holdings_accounting_blueprint.holdings_accounting",
            guided=1,
            mode="declare" if blocker_type == "Current holdings missing" else "reconcile",
        )
    if blocker_type in {"Import warning decision", "Reviewed import warning blocker", "Possible overlapping source files"}:
        return url_for("import_transactions_blueprint.import_wizard", guided=1) + "#import_warning_workflow"
    if blocker_type == "Tax evidence review":
        return url_for("tax_filing_review_blueprint.index")
    return url_for("export_blueprint.index", guided=1)


def _work_order_item_title(row):
    blocker_type = row.get("blocker_type")
    asset = row.get("asset") or ""
    year = row.get("year") or ""
    source_file = row.get("source_file") or ""

    if blocker_type == "Missing acquisition basis":
        return f"Resolve {asset} missing cost basis" if asset else "Resolve missing cost basis"
    if blocker_type == "Holdings explanation needed":
        return f"Explain the {asset} holdings gap" if asset else "Explain a holdings gap"
    if blocker_type == "Current holdings missing":
        return f"Enter current {asset} holdings" if asset else "Enter current holdings"
    if blocker_type == "Import warning decision":
        return f"Decide what happened in {source_file}" if source_file else "Decide what happened in an import row"
    if blocker_type == "Reviewed import warning blocker":
        return f"Resolve reviewed warning in {source_file}" if source_file else "Resolve a reviewed import warning"
    if blocker_type == "Possible overlapping source files":
        return "Decide whether source files overlap"
    if blocker_type == "Tax evidence review":
        return f"Review {year} tax evidence" if year else "Review tax evidence"

    return row.get("blocker_type") or "Review packet item"


def _work_order_item_question(row):
    blocker_type = row.get("blocker_type")
    asset = row.get("asset") or "this asset"
    year = row.get("year") or "this year"

    questions = {
        "Missing acquisition basis": (
            f"Gainz found {asset} sales, but not the {asset} acquisition history. Can you prove the basis, "
            "confirm it was already filed, or treat the unknown basis conservatively for CPA review?"
        ),
        "Holdings explanation needed": (
            f"Why does Gainz calculate a different {asset} balance than you declared: missing transfer, disposal, loss, "
            "gift, duplicate source file, or another source record?"
        ),
        "Current holdings missing": (
            f"What amount of {asset} do you currently hold across exchanges, wallets, and custody accounts?"
        ),
        "Import warning decision": (
            "Does this source row belong in the review, and if so does it need corrected columns, a manual USD value, "
            "or a source-backed manual row?"
        ),
        "Reviewed import warning blocker": (
            "You already made a warning decision, but what evidence or correction is still needed before this stops blocking the packet?"
        ),
        "Possible overlapping source files": (
            "Do these source files duplicate the same activity, or do they represent different accounts or date ranges?"
        ),
        "Tax evidence review": (
            f"What filed return, Form 8949/Schedule D, payment evidence, workbook, or zero-year confirmation supports {year}?"
        ),
    }
    return questions.get(blocker_type, "What should be documented before treating this item as reviewed?")


def _work_order_item_summary(row):
    parts = []
    for label, value in (
        ("Asset", row.get("asset")),
        ("Year", row.get("year")),
        ("Date", row.get("date")),
        ("Source", row.get("source_file")),
        ("Issue", row.get("suspected_issue")),
    ):
        value = str(value or "").strip()
        if value:
            parts.append({"label": label, "value": value})
    return parts


def _professional_review_options(row):
    blocker_type = row.get("blocker_type")
    asset = row.get("asset") or "this asset"
    year = row.get("year") or "the affected year"

    options_by_type = {
        "Missing acquisition basis": [
            (
                "Reconstruct basis from records",
                (
                    f"Look for earlier {asset} exchange CSVs, wallet receives, broker forms, tax software exports, "
                    "email receipts, CPA workbooks, income/fork/airdrop records, or transfer-in records before the sale."
                ),
            ),
            (
                "Correct source classification",
                (
                    "If this row is not actually a taxable disposal, correct the import or add source-backed manual rows "
                    "so Gainz is not treating the wrong activity as a sale."
                ),
            ),
            (
                "Apply a professionally directed basis adjustment",
                (
                    "When records cannot be reconstructed, the CPA can document a supported acquisition date, proceeds, "
                    "basis treatment, and workpaper. Gainz can then apply that exact resolution to the sale and Form 8949 output. "
                    "The user records the direction; Gainz does not verify the professional's identity or credentials."
                ),
            ),
            (
                "Compare against filed tax records",
                (
                    f"Compare {year} filed Form 8949/Schedule D, tax software worksheets, or CPA files to determine whether "
                    "the original filing already addressed this disposal or whether follow-up is needed."
                ),
            ),
        ],
        "Holdings explanation needed": [
            (
                "Trace transfers",
                "Review destination wallet or exchange records to determine whether sends stayed under the taxpayer's control.",
            ),
            (
                "Identify disposals",
                "Determine whether documented sends were sales, trades, payments, gifts, losses, or another taxable/non-taxable event.",
            ),
            (
                "Remove duplicate activity",
                "Check whether overlapping CSV exports are duplicating buys, sells, receives, or sends.",
            ),
        ],
        "Tax evidence review": [
            (
                "Confirm filed totals",
                f"Compare Gainz totals with filed return, Form 8949, Schedule D, payment evidence, or CPA workpapers for {year}.",
            ),
            (
                "Mark zero or not applicable",
                "If there was no reportable digital-asset activity for the year, document that confirmation.",
            ),
        ],
    }

    return options_by_type.get(blocker_type, [])


def _tax_cross_check_for_item(transactions, row):
    year_value = row.get("year")
    if year_value in (None, ""):
        return None

    try:
        year = int(year_value)
    except (TypeError, ValueError):
        return None

    alignment = get_tax_filing_alignment_summary(transactions)
    alignment_row = next(
        (item for item in alignment.get("rows", []) if int(item.get("year", 0)) == year),
        None,
    )
    if not alignment_row:
        return None

    has_filed_totals = bool(alignment_row.get("has_record"))
    if has_filed_totals:
        headline = f"{year} filed evidence is recorded"
        guidance = (
            "Use this as a cross-check while reviewing the gap. If a source-backed classification moves Gainz closer "
            "to filed Form 8949/Schedule D totals, that can support the review trail. If it moves farther away, review "
            "source records before relying on the classification."
        )
    else:
        headline = f"No filed totals recorded for {year}"
        guidance = (
            "You can still review this gap from source records. Add filed Form 8949/Schedule D totals later to compare "
            "whether Gainz's calculated totals align with what was originally filed."
        )

    return {
        "year": year,
        "headline": headline,
        "status": alignment_row.get("status", ""),
        "status_class": alignment_row.get("status_class", ""),
        "guidance": guidance,
        "calculated_rows": alignment_row.get("calculated_rows", 0),
        "calculated_proceeds_display": alignment_row.get("calculated_proceeds_display", "$0.00"),
        "calculated_cost_basis_display": alignment_row.get("calculated_cost_basis_display", "$0.00"),
        "calculated_gain_loss_display": alignment_row.get("calculated_gain_loss_display", "$0.00"),
        "reported_proceeds_display": alignment_row.get("reported_proceeds_display") or "Not recorded",
        "reported_cost_basis_display": alignment_row.get("reported_cost_basis_display") or "Not recorded",
        "reported_gain_loss_display": alignment_row.get("reported_gain_loss_display") or "Not recorded",
        "difference_gain_loss_display": alignment_row.get("difference_gain_loss_display") or "N/A",
        "tax_paid_display": alignment_row.get("tax_paid_display") or "Not recorded",
        "evidence_reference": alignment_row.get("evidence_reference") or "Not recorded",
        "next_action": alignment_row.get("next_action", ""),
        "has_filed_totals": has_filed_totals,
    }


def _review_queue_choices_for_item(row):
    blocker_type = (row or {}).get("blocker_type")
    asset = (row or {}).get("asset") or "this asset"
    values_by_type = {
        "Missing acquisition basis": [
            "import_missing_records",
            "fork_airdrop_basis",
            "already_in_filed_totals",
            "zero_basis_cpa_review",
            "conservative_max_gain",
            "sent_to_cpa",
            "resolved",
        ],
        "Holdings explanation needed": [
            "import_missing_records",
            "classify_documented_disposal",
            "keep_owner_transfer",
            "needs_research",
            "sent_to_cpa",
            "ignored_for_draft",
            "resolved",
        ],
        "Current holdings missing": [
            "resolved",
            "needs_research",
            "sent_to_cpa",
        ],
        "Import warning decision": [
            "resolved",
            "import_missing_records",
            "needs_research",
            "ignored_for_draft",
            "sent_to_cpa",
        ],
        "Reviewed import warning blocker": [
            "resolved",
            "import_missing_records",
            "needs_research",
            "ignored_for_draft",
            "sent_to_cpa",
        ],
        "Possible overlapping source files": [
            "resolved",
            "needs_research",
            "ignored_for_draft",
            "sent_to_cpa",
        ],
        "Tax evidence review": [
            "resolved",
            "import_missing_records",
            "needs_research",
            "ignored_for_draft",
            "sent_to_cpa",
        ],
    }
    values = values_by_type.get(blocker_type)
    if not values:
        return work_order_review_choices()

    label_overrides = {
        "Missing acquisition basis": {
            "import_missing_records": f"Import missing {asset} acquisition records",
            "fork_airdrop_basis": f"This {asset} came from a fork/airdrop",
            "already_in_filed_totals": "Already included in filed tax totals",
            "zero_basis_cpa_review": "Document conservative $0 basis for CPA review",
            "conservative_max_gain": "Apply conservative $0-basis short-term treatment",
            "sent_to_cpa": f"Send this {asset} gap to CPA",
            "resolved": "Apply Professional-Directed Treatment",
        },
        "Holdings explanation needed": {
            "import_missing_records": "I will import missing records",
            "classify_documented_disposal": "Classify documented send as disposal",
            "keep_owner_transfer": "Keep as owner transfer",
            "needs_research": "I do not know yet / needs research",
            "sent_to_cpa": "Send this question to CPA",
            "ignored_for_draft": "Leave unresolved for draft only",
            "resolved": "Already resolved",
        },
        "Current holdings missing": {
            "resolved": "Current holdings are entered",
            "needs_research": "I do not know yet / needs research",
            "sent_to_cpa": "Send this question to CPA",
        },
    }

    return [
        {
            "value": value,
            "label": label_overrides.get(blocker_type, {}).get(value, WORK_ORDER_REVIEW_DECISIONS[value]),
        }
        for value in values
        if value in WORK_ORDER_REVIEW_DECISIONS
    ]


def _review_queue_context(transactions, item_id=""):
    rows = _work_order_rows(transactions)
    unreviewed = [row for row in rows if not row.get("review_decision")]
    current = None

    if item_id:
        current = next((row for row in rows if row.get("item_id") == item_id), None)

    if current is None:
        current = unreviewed[0] if unreviewed else None

    index = (
        unreviewed.index(current) + 1
        if current in unreviewed
        else rows.index(current) + 1 if current in rows else 0
    )
    next_item = None
    if current and unreviewed:
        current_position = rows.index(current)
        later_unreviewed = [
            row for row in rows[current_position + 1 :]
            if not row.get("review_decision") and row.get("item_id") != current.get("item_id")
        ]
        next_item = later_unreviewed[0] if later_unreviewed else next(
            (row for row in unreviewed if row.get("item_id") != current.get("item_id")),
            None,
        )
    if current:
        current["why_it_matters"] = _work_order_why_it_matters(current)
        current["related_url"] = _work_order_related_url(current)
        current["review_title"] = _work_order_item_title(current)
        current["review_question"] = _work_order_item_question(current)
        current["review_summary"] = _work_order_item_summary(current)
        current["professional_review_options"] = _professional_review_options(current)
        current["tax_cross_check"] = _tax_cross_check_for_item(transactions, current)
        current["show_cpa_resolution"] = current.get("blocker_type") in {
            "Missing acquisition basis",
            "Holdings explanation needed",
        }
        if current["show_cpa_resolution"]:
            current["direction_date"] = current.get("direction_date") or datetime.date.today().isoformat()
            entered_by = str(getattr(current_user, "username", "") or "").strip()
            current["direction_entered_by"] = (
                current.get("direction_entered_by") or entered_by or "Local Gainz user"
            )
        if current.get("blocker_type") == "Missing acquisition basis":
            target_sell = next(
                (
                    trans
                    for trans in transactions
                    if trans.uid == current.get("target_transaction_uid")
                    and trans.trans_type == "sell"
                ),
                None,
            )
            if target_sell is not None:
                unresolved_quantity = float(current.get("quantity") or 0)
                transaction_quantity = float(target_sell.quantity or 0)
                supported_links = [
                    link
                    for link in getattr(target_sell, "links", []) or []
                    if getattr(link, "sell", None) is target_sell
                ]
                supported_quantity = sum(float(link.quantity or 0) for link in supported_links)
                supported_proceeds = sum(float(link.proceeds or 0) for link in supported_links)
                supported_basis = sum(float(link.cost_basis or 0) for link in supported_links)
                supported_gain_loss = supported_proceeds - supported_basis
                full_gross = float(target_sell.gross_usd_total or 0)
                full_fee = float(target_sell.prorated_fee_usd(transaction_quantity) or 0)
                full_net = float(target_sell.tax_usd_total or 0)
                unresolved_proceeds = float(target_sell.prorated_tax_usd(unresolved_quantity) or 0)
                unresolved_fee = float(target_sell.prorated_fee_usd(unresolved_quantity) or 0)
                current["sale_split"] = {
                    "full_quantity": transaction_quantity,
                    "full_gross": full_gross,
                    "full_fee": full_fee,
                    "full_net": full_net,
                    "supported_quantity": supported_quantity,
                    "supported_proceeds": supported_proceeds,
                    "supported_basis": supported_basis,
                    "supported_gain_loss": supported_gain_loss,
                    "unresolved_quantity": unresolved_quantity,
                    "unresolved_proceeds": unresolved_proceeds,
                    "unresolved_fee": unresolved_fee,
                }
                current["source_proceeds_value"] = f"{target_sell.prorated_tax_usd(unresolved_quantity):.2f}"
                if not current.get("proceeds_value"):
                    current["proceeds_value"] = current["source_proceeds_value"]
                if not current.get("proceeds_method"):
                    current["proceeds_method"] = (
                        "allocated_source_value"
                        if unresolved_quantity + 0.00000001 < transaction_quantity
                        else "source_reported"
                    )
                if unresolved_quantity + 0.00000001 < transaction_quantity:
                    current["proceeds_allocation_explanation"] = (
                        f"Calculated suggestion: {unresolved_quantity:.8f} {target_sell.symbol} / "
                        f"{transaction_quantity:.8f} {target_sell.symbol} x ${full_net:.2f} imported net "
                        f"proceeds = ${unresolved_proceeds:.2f}. This is a proportional allocation from "
                        "the source transaction, not a separately source-reported amount. Confirm it "
                        "before applying a treatment."
                    )
                else:
                    current["proceeds_allocation_explanation"] = (
                        f"The imported source transaction reports ${full_net:.2f} of net proceeds "
                        f"after ${full_fee:.2f} of fees for this full quantity."
                    )
                if not current.get("acquisition_date_method"):
                    current["acquisition_date_method"] = "documented_date"
        choices = _review_queue_choices_for_item(current)
        current["allowed_outcomes"] = [choice["label"] for choice in choices]
    else:
        choices = work_order_review_choices()

    applied_resolutions = []
    for review in getattr(transactions, "work_order_reviews", []) or []:
        if str(review.get("calculation_applied") or "") != "Yes":
            continue
        receipt = {}
        try:
            receipt = json.loads(review.get("calculation_receipt_json") or "{}")
        except (TypeError, ValueError):
            receipt = {}
        applied_resolutions.append({
            **review,
            "decision_label": WORK_ORDER_REVIEW_DECISIONS.get(review.get("decision"), review.get("decision", "")),
            "receipt": receipt,
        })

    active_ids = {str(row.get("item_id") or "") for row in rows}
    review_records = {
        str(review.get("item_id") or ""): review
        for review in getattr(transactions, "work_order_reviews", []) or []
        if str(review.get("item_id") or "")
    }
    stable_ids = active_ids | set(review_records)
    resolved_ids = set()
    deferred_ids = set()
    unresolved_ids = {
        str(row.get("item_id") or "")
        for row in rows
        if not row.get("review_decision")
    }
    for stable_item_id in stable_ids:
        review = review_records.get(stable_item_id) or {}
        decision = str(review.get("decision") or "")
        if str(review.get("calculation_applied") or "") == "Yes":
            resolved_ids.add(stable_item_id)
        elif stable_item_id not in active_ids and decision:
            resolved_ids.add(stable_item_id)
        elif stable_item_id in active_ids and decision:
            deferred_ids.add(stable_item_id)

    return {
        "rows": rows,
        "item": current,
        "index": index,
        "total": len(stable_ids),
        "active_total": len(rows),
        "unreviewed_count": len(unresolved_ids),
        "reviewed_count": len(resolved_ids) + len(deferred_ids),
        "resolved_count": len(resolved_ids),
        "deferred_count": len(deferred_ids),
        "next_item_id": next_item.get("item_id") if next_item else "",
        "choices": choices,
        "cpa_resolution_choices": cpa_resolution_choices(),
        "applied_resolutions": applied_resolutions,
    }


def _packet_manifest_counts(packet_path):
    counts = {
        "copied_files": 0,
        "reference_only_tax_evidence": 0,
        "missing_tax_evidence": 0,
    }
    manifest_path = packet_path / "03_manifests" / "evidence_manifest.csv"
    if not manifest_path.exists():
        return counts

    with open(manifest_path, newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row.get("status") == "COPIED":
                counts["copied_files"] += 1
            if row.get("category") == "tax_evidence" and row.get("status") == "REFERENCE_ONLY":
                counts["reference_only_tax_evidence"] += 1
            if row.get("category") == "tax_evidence" and row.get("status") == "MISSING":
                counts["missing_tax_evidence"] += 1
    return counts


def _folder_size(path):
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _format_bytes(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _packet_success_context(packet_path):
    summary = {}
    summary_path = packet_path / "03_manifests" / "audit_packet_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    counts = _packet_manifest_counts(packet_path)
    is_ready = bool(summary.get("readiness_is_ready"))
    blocker_groups = summary.get("readiness_blocker_groups") or []
    packet_size = _folder_size(packet_path)
    generated_at = ""
    if packet_path.exists():
        generated_at = datetime.datetime.fromtimestamp(packet_path.stat().st_mtime).strftime("%Y-%m-%d %I:%M %p")
    review_first = [
        "README_FIRST.md for the human packet orientation.",
        "PACKET_STATUS.md for readiness, blockers, warnings, and evidence counts.",
        "FOR_CPAS.md for the CPA-facing review order.",
        "03_manifests/evidence_manifest.csv for copied, reference-only, and missing evidence.",
        "01_reports/reconciliation_work_order.csv for unresolved review items.",
    ]

    return {
        "packet_path": str(packet_path),
        "packet_name": packet_path.name,
        "readme_first_path": str(packet_path / "README_FIRST.md"),
        "packet_exists": packet_path.exists() and packet_path.is_dir(),
        "status": packet_review_status(is_ready),
        "status_class": "status-verified" if is_ready else "status-needs-review",
        "is_draft": not is_ready,
        "summary": summary.get("readiness_summary", "Open the packet status file for details."),
        "generated_at": generated_at or "Unknown",
        "packet_size": _format_bytes(packet_size),
        "copied_files_count": counts["copied_files"],
        "reference_only_files_count": counts["reference_only_tax_evidence"],
        "missing_evidence_count": counts["missing_tax_evidence"],
        "open_blocker_groups": blocker_groups,
        "material_assumptions": summary.get("material_assumptions") or [],
        "review_first": review_first,
        "cpa_summary": (
            f"Gainz audit packet: {packet_review_status(is_ready).lower()}. "
            f"Packet path: {packet_path}. "
            f"Summary: {summary.get('readiness_summary', 'Open PACKET_STATUS.md for details.')}. "
            f"Copied files: {counts['copied_files']}. "
            f"Reference-only tax evidence records: {counts['reference_only_tax_evidence']}. "
            f"Missing evidence paths: {counts['missing_tax_evidence']}. "
            "Recommended first files: README_FIRST.md, PACKET_STATUS.md, FOR_CPAS.md, "
            "03_manifests/evidence_manifest.csv, and 01_reports/reconciliation_work_order.csv."
        ),
    }


@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)
    audit_readiness = get_audit_readiness_summary(transactions)
    default_output_folder = _path_for_display(_default_packet_output_folder())
    work_order_rows = _work_order_rows(transactions)

    return render_template(
        'export.html',
        stats_table_data=stats_table_data,
        audit_readiness=audit_readiness,
        export_folder=_path_for_display(current_app.config['EXPORT_FOLDER']),
        audit_packet_folder=_path_for_display(current_app.config['AUDIT_PACKET_FOLDER']),
        detected_tax_folder=_detected_tax_folder(),
        output_location_choices=[
            {
                "value": value,
                "label": {
                    "detected_taxes": "Detected Taxes folder",
                    "audit_packets": "Gainz audit packet folder",
                    "exports": "Gainz workbook export folder",
                }.get(value, value),
                "path": _path_for_display(path),
                "selected": (
                    value == "detected_taxes"
                    if _detected_tax_folder()
                    else value == "audit_packets"
                ),
            }
            for value, path in _output_location_choices().items()
        ],
        packet_preview=get_packet_preview(transactions, audit_readiness, default_output_folder),
        work_order_rows=work_order_rows,
        work_order_review_choices=work_order_review_choices(),
    )


@blueprint.route('/work_order_review', methods=['POST'])
@login_required
def work_order_review():
    transactions = current_app.config['transactions']
    payload = request.get_json(silent=True) or {}
    source = payload if request.is_json else request.form
    item_id = str(source.get("item_id") or "").strip()
    decision = str(source.get("decision") or "").strip()
    note = str(source.get("note") or "").strip()
    cpa_question = str(source.get("cpa_question") or "").strip()

    if not item_id:
        if request.is_json:
            return jsonify({"message": "Work order item id is required."}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    if decision not in WORK_ORDER_REVIEW_DECISIONS:
        if request.is_json:
            return jsonify({"message": "Choose a valid work order review state."}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    details, detail_error = _cpa_resolution_details(source)
    item = next(
        (row for row in _work_order_rows(transactions) if row.get("item_id") == item_id),
        None,
    )
    if item is None:
        if request.is_json:
            return jsonify({"message": "The work order item is no longer open. Refresh before saving."}), 409
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))
    validation_error = detail_error or _validate_cpa_resolution(
        item or {},
        decision,
        details,
        note=note,
    )
    validation_error = validation_error or _apply_cpa_calculation_resolution(
        transactions,
        item,
        item_id,
        decision,
        details,
    )
    if validation_error:
        if request.is_json:
            return jsonify({"message": validation_error}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    transactions.set_work_order_review(
        item_id,
        decision=decision,
        note=note,
        cpa_question=cpa_question,
        **_work_order_context_fields(item),
        **details,
    )
    transactions.save(description=f"Updated work order item: {WORK_ORDER_REVIEW_DECISIONS[decision]}")

    if request.is_json:
        return jsonify({
            "item_id": item_id,
            "decision": decision,
            "decision_label": WORK_ORDER_REVIEW_DECISIONS[decision],
        })

    return redirect(url_for('export_blueprint.index', work_order_reviewed=1))


@blueprint.route('/review_queue', methods=['GET'])
@login_required
def review_queue():
    transactions = current_app.config['transactions']
    context = _review_queue_context(transactions, item_id=request.args.get("item_id", ""))
    return render_template("review_queue.html", **context)


@blueprint.route('/review_queue/save', methods=['POST'])
@login_required
def review_queue_save():
    transactions = current_app.config['transactions']
    item_id = str(request.form.get("item_id") or "").strip()
    decision = str(request.form.get("decision") or "").strip()
    workflow_action = str(request.form.get("workflow_action") or "apply").strip()
    note = str(request.form.get("note") or "").strip()
    cpa_question = str(request.form.get("cpa_question") or "").strip()

    if not item_id or decision not in WORK_ORDER_REVIEW_DECISIONS:
        return redirect(url_for('export_blueprint.review_queue', guided=1, item_id=item_id, saved=0))

    details, detail_error = _cpa_resolution_details(request.form)
    item = next(
        (row for row in _work_order_rows(transactions) if row.get("item_id") == item_id),
        None,
    )
    if item is None:
        context = _review_queue_context(transactions)
        context["save_error"] = "That review item is no longer open. Continue with the next item."
        return render_template("review_queue.html", **context), 409

    if workflow_action == "configure":
        context = _resolution_form_context(
            transactions,
            item_id,
            decision,
            note=note,
            cpa_question=cpa_question,
        )
        return render_template("review_queue.html", **context)

    validation_error = detail_error or _validate_cpa_resolution(
        item or {},
        decision,
        details,
        note=note,
        for_preview=workflow_action == "preview",
    )
    if not validation_error and workflow_action == "preview":
        context = _resolution_form_context(
            transactions,
            item_id,
            decision,
            details=details,
            note=note,
            cpa_question=cpa_question,
        )
        context["resolution_preview"] = _resolution_impact_preview(
            transactions,
            item,
            decision,
            details,
        )
        session["gainz_resolution_preview"] = {
            "item_id": item_id,
            "fingerprint": _resolution_preview_fingerprint(
                item,
                decision,
                details,
                note=note,
                cpa_question=cpa_question,
            ),
        }
        return render_template("review_queue.html", **context)

    preview_required = bool(item.get("blocker_type") in {
        "Missing acquisition basis",
        "Holdings explanation needed",
    })
    if workflow_action == "apply" and preview_required and not validation_error:
        pending_preview = session.get("gainz_resolution_preview") or {}
        expected_fingerprint = _resolution_preview_fingerprint(
            item,
            decision,
            details,
            note=note,
            cpa_question=cpa_question,
        )
        if (
            pending_preview.get("item_id") != item_id
            or pending_preview.get("fingerprint") != expected_fingerprint
        ):
            validation_error = (
                "Review the current before/after impact before applying this treatment. "
                "If any field changed, generate a new preview."
            )
        elif not _truthy_payload_value(request.form.get("preview_confirmed")):
            validation_error = "Review the calculation impact and confirm it before applying this treatment."
    validation_error = validation_error or _apply_cpa_calculation_resolution(
        transactions,
        item,
        item_id,
        decision,
        details,
    )
    if validation_error:
        context = _resolution_form_context(
            transactions,
            item_id,
            decision,
            details=details,
            note=note,
            cpa_question=cpa_question,
        )
        context["save_error"] = validation_error
        return render_template("review_queue.html", **context), 400

    transactions.set_work_order_review(
        item_id,
        decision=decision,
        note=note,
        cpa_question=cpa_question,
        **_work_order_context_fields(item),
        **details,
    )
    transactions.save(description=f"Updated review queue item: {WORK_ORDER_REVIEW_DECISIONS[decision]}")
    session.pop("gainz_resolution_preview", None)

    return redirect(url_for('export_blueprint.review_queue', guided=1, saved=1))


@blueprint.route('/review_queue/reverse', methods=['POST'])
@login_required
def review_queue_reverse():
    transactions = current_app.config['transactions']
    item_id = str(request.form.get("item_id") or "").strip()
    note = str(request.form.get("reversal_note") or "").strip()
    try:
        transactions.reverse_work_order_resolution(item_id, note=note)
        transactions.save(description="Reversed professional calculation resolution")
    except ValueError:
        context = _review_queue_context(transactions)
        context["save_error"] = (
            "Gainz could not reverse that resolution. Refresh the queue and confirm the applied resolution still exists."
        )
        return render_template("review_queue.html", **context), 400
    return redirect(url_for('export_blueprint.review_queue', guided=1, reversed=1))


@blueprint.route('/packet_preview.json', methods=['GET', 'POST'])
@login_required
def packet_preview_json():
    transactions = current_app.config['transactions']
    try:
        output_dir = _output_dir_for_location(_default_packet_output_folder())
    except ValueError:
        return jsonify({"message": "Choose an available local Gainz output folder."}), 400

    readiness = get_audit_readiness_summary(transactions)
    return jsonify({
        "packet_preview": get_packet_preview(transactions, readiness, output_dir),
        "readiness": {
            "status": readiness["status"],
            "status_class": readiness["status_class"],
            "is_ready": readiness["is_ready"],
            "summary": readiness["summary"],
            "next_action": readiness["next_action"],
            "blocker_groups": readiness["blocker_groups"],
            "metrics": readiness["metrics"],
        },
    })


@blueprint.route('/save',  methods=['POST'])
@login_required
def save():
    transactions = current_app.config['transactions']
    draft_error = _draft_ack_error(transactions, "Workbook export")
    if draft_error:
        return draft_error

    try:
        output_dir = _output_dir_for_location(_default_packet_output_folder(), create=True)
    except ValueError:
        return jsonify({"message": "Choose an available local Gainz output folder."}), 400

    readiness = get_audit_readiness_summary(transactions)
    save_as_filename = ExportService(str(output_dir)).export_to_excel(
        transactions,
        readiness=readiness,
    )
    if not readiness["is_ready"]:
        save_as_filename = _draft_workbook_path(save_as_filename)

    print(f"exporting to {save_as_filename}")

    return jsonify({
        "path": save_as_filename,
        "output_dir": str(output_dir),
    })


@blueprint.route('/audit_packet',  methods=['POST'])
@login_required
def audit_packet():
    transactions = current_app.config['transactions']
    draft_error = _draft_ack_error(transactions, "Audit packet")
    if draft_error:
        return draft_error

    try:
        output_dir = _output_dir_for_location(_default_packet_output_folder(), create=True)
    except ValueError:
        return jsonify({"message": "Choose an available local Gainz output folder."}), 400

    packet_path = AuditPacketService(
        str(output_dir),
        str(output_dir),
    ).create_packet(transactions)
    session["last_packet_path"] = str(Path(packet_path).resolve())

    return jsonify({
        "path": packet_path,
        "output_dir": str(output_dir),
        "success_url": url_for("export_blueprint.packet_success", guided=1) if _guided_requested() else url_for("export_blueprint.packet_success"),
    })


@blueprint.route('/packet_success', methods=['GET'])
@login_required
def packet_success():
    packet_path = _last_packet_path()
    if not packet_path:
        if _guided_requested():
            return redirect(url_for("export_blueprint.index", guided=1))
        return redirect(url_for("export_blueprint.index"))

    return render_template(
        "packet_success.html",
        packet=_packet_success_context(packet_path),
        open_request=request.args.get("opened"),
    )


@blueprint.route('/open_folder', methods=['POST'])
@login_required
def open_folder():
    packet_path = _last_packet_path()
    if packet_path:
        _open_existing_local_path(packet_path)
    if _guided_requested():
        return redirect(url_for("export_blueprint.packet_success", guided=1, opened="folder"))
    return redirect(url_for("export_blueprint.packet_success", opened="folder"))


@blueprint.route('/open_path', methods=['POST'])
@login_required
def open_path():
    packet_path = _last_packet_path()
    if packet_path:
        _open_existing_local_path(packet_path / "README_FIRST.md")
    if _guided_requested():
        return redirect(url_for("export_blueprint.packet_success", guided=1, opened="readme"))
    return redirect(url_for("export_blueprint.packet_success", opened="readme"))

