import csv
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

from . import blueprint
from flask import render_template, request, jsonify, current_app, redirect, session, url_for
from flask_login import login_required
from utils import *
from app.services.export_service import ExportService
from app.services.audit_packet_service import AuditPacketService
from app.services.packet_plan_service import (
    WORK_ORDER_REVIEW_DECISIONS,
    get_packet_preview,
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
            f"Can you find earlier {asset} buy, receive, income, fork, airdrop, or transfer-in records "
            "for this sale, or should this remain documented as unknown/research for CPA review?"
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
                "Document unsupported or unknown basis",
                (
                    "If records cannot be reconstructed, leave the item as a draft blocker with notes describing what was checked "
                    "and what remains unknown for professional review."
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
    values_by_type = {
        "Missing acquisition basis": [
            "import_missing_records",
            "document_unknown_basis",
            "needs_research",
            "sent_to_cpa",
            "ignored_for_draft",
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
            "import_missing_records": "I will import or add missing records",
            "document_unknown_basis": "Document unknown basis",
            "needs_research": "I do not know yet / needs research",
            "sent_to_cpa": "Ask CPA to determine basis treatment",
            "ignored_for_draft": "Leave unresolved for draft only",
            "resolved": "Already resolved",
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

    index = rows.index(current) + 1 if current in rows else 0
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
        choices = _review_queue_choices_for_item(current)
        current["allowed_outcomes"] = [choice["label"] for choice in choices]
    else:
        choices = work_order_review_choices()

    return {
        "rows": rows,
        "item": current,
        "index": index,
        "total": len(rows),
        "unreviewed_count": len(unreviewed),
        "reviewed_count": len(rows) - len(unreviewed),
        "next_item_id": next_item.get("item_id") if next_item else "",
        "choices": choices,
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
        "status": "Filing-ready review packet" if is_ready else "Draft packet",
        "status_class": "status-verified" if is_ready else "status-needs-review",
        "is_draft": not is_ready,
        "summary": summary.get("readiness_summary", "Open the packet status file for details."),
        "generated_at": generated_at or "Unknown",
        "packet_size": _format_bytes(packet_size),
        "copied_files_count": counts["copied_files"],
        "reference_only_files_count": counts["reference_only_tax_evidence"],
        "missing_evidence_count": counts["missing_tax_evidence"],
        "open_blocker_groups": blocker_groups,
        "review_first": review_first,
        "cpa_summary": (
            f"Gainz audit packet: {'filing-ready review packet' if is_ready else 'draft packet'}. "
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
    item_id = str(payload.get("item_id") or request.form.get("item_id") or "").strip()
    decision = str(payload.get("decision") or request.form.get("decision") or "").strip()
    note = str(payload.get("note") or request.form.get("note") or "").strip()
    cpa_question = str(payload.get("cpa_question") or request.form.get("cpa_question") or "").strip()

    if not item_id:
        if request.is_json:
            return jsonify({"message": "Work order item id is required."}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    if decision not in WORK_ORDER_REVIEW_DECISIONS:
        if request.is_json:
            return jsonify({"message": "Choose a valid work order review state."}), 400
        return redirect(url_for('export_blueprint.index', work_order_reviewed=0))

    transactions.set_work_order_review(
        item_id,
        decision=decision,
        note=note,
        cpa_question=cpa_question,
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
    note = str(request.form.get("note") or "").strip()
    cpa_question = str(request.form.get("cpa_question") or "").strip()

    if not item_id or decision not in WORK_ORDER_REVIEW_DECISIONS:
        return redirect(url_for('export_blueprint.review_queue', guided=1, item_id=item_id, saved=0))

    transactions.set_work_order_review(
        item_id,
        decision=decision,
        note=note,
        cpa_question=cpa_question,
    )
    transactions.save(description=f"Updated review queue item: {WORK_ORDER_REVIEW_DECISIONS[decision]}")

    return redirect(url_for('export_blueprint.review_queue', guided=1, saved=1))


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

