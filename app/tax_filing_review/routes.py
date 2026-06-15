import os
from pathlib import Path

from flask import current_app, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from utils import get_tax_filing_alignment_summary, parse_float_value
from app.services.tax_evidence_service import (
    TAX_EVIDENCE_TYPE_CHOICES,
    classify_tax_evidence,
    get_tax_evidence_inventory_summary,
    infer_tax_evidence_year,
    tax_evidence_type_label,
)
from app.services.tax_filing_import_service import import_tax_total_records
from app.services.tax_total_extraction_service import get_suggested_filed_totals

from . import blueprint


TAX_EVIDENCE_SCAN_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".txt", ".png", ".jpg", ".jpeg"}


def _available_years(alignment):
    years = {row["year"] for row in alignment["rows"]}
    return sorted(years, reverse=True)


def _optional_year(value, *fallback_values):
    if value not in (None, ""):
        try:
            return int(value)
        except (TypeError, ValueError):
            pass

    return infer_tax_evidence_year(*fallback_values)


def _tax_evidence_upload_dir():
    upload_dir = Path(current_app.config.get("INSTANCE_PATH", current_app.instance_path)) / "tax_evidence"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _save_uploaded_evidence(file_storage):
    if not file_storage or not file_storage.filename:
        return ""

    safe_name = secure_filename(file_storage.filename)
    if not safe_name:
        return ""

    destination = _tax_evidence_upload_dir() / safe_name
    if destination.exists():
        stem = destination.stem
        suffix = destination.suffix
        index = 2
        while destination.exists():
            destination = _tax_evidence_upload_dir() / f"{stem}_{index}{suffix}"
            index += 1

    file_storage.save(destination)
    return str(destination)


def _add_tax_evidence_record(transactions, year, reference, evidence_type, notes):
    evidence_type = classify_tax_evidence(reference, notes, evidence_type)
    record_year = _optional_year(year, reference, notes)
    label = os.path.basename(str(reference)) if reference else tax_evidence_type_label(evidence_type)

    return transactions.set_tax_evidence_record(
        year=record_year,
        evidence_type=evidence_type,
        evidence_label=label,
        evidence_path=reference if os.path.exists(str(reference)) else "",
        notes=notes,
    )


def _money_from_form_or_existing(form_name, record_field, existing_record):
    raw_value = request.form.get(form_name)
    if raw_value in (None, "") and existing_record:
        return existing_record.get(record_field)

    return parse_float_value(raw_value)


def _existing_text_or_form(form_name, record_field, existing_record):
    raw_value = request.form.get(form_name)
    if raw_value in (None, "") and existing_record:
        return existing_record.get(record_field, "")

    return raw_value or ""


@blueprint.route('/', methods=['GET'])
@login_required
def index():
    transactions = current_app.config['transactions']
    alignment = get_tax_filing_alignment_summary(transactions)
    evidence_inventory = get_tax_evidence_inventory_summary(transactions, alignment)
    suggested_totals = get_suggested_filed_totals(transactions)

    return render_template(
        'tax_filing_review.html',
        alignment=alignment,
        evidence_inventory=evidence_inventory,
        suggested_totals=suggested_totals,
        evidence_type_choices=TAX_EVIDENCE_TYPE_CHOICES,
        available_years=_available_years(alignment),
        saved_year=request.args.get("saved_year"),
        saved_evidence=request.args.get("saved_evidence"),
        saved_suggestion=request.args.get("saved_suggestion"),
        imported_tax_rows=request.args.get("imported_tax_rows"),
        skipped_tax_rows=request.args.get("skipped_tax_rows"),
        tax_import_error=request.args.get("tax_import_error"),
    )


@blueprint.route('/save', methods=['POST'])
@login_required
def save_tax_year_record():
    transactions = current_app.config['transactions']
    year = int(request.form.get("year"))

    transactions.set_tax_year_record(
        year=year,
        reported_proceeds=parse_float_value(request.form.get("reported_proceeds")),
        reported_cost_basis=parse_float_value(request.form.get("reported_cost_basis")),
        reported_gain_loss=parse_float_value(request.form.get("reported_gain_loss")),
        tax_paid=parse_float_value(request.form.get("tax_paid")),
        filing_status=request.form.get("filing_status") or "Filed",
        evidence_reference=request.form.get("evidence_reference") or "",
        notes=request.form.get("notes") or "",
    )
    transactions.save(description=f"Recorded filed tax totals for {year}")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_year=year))


@blueprint.route('/suggested_totals/confirm', methods=['POST'])
@login_required
def confirm_suggested_filed_totals():
    transactions = current_app.config['transactions']
    year = int(request.form.get("year"))
    existing_record = transactions.get_tax_year_record(year)
    source_reference = request.form.get("source_reference") or ""
    source_note = request.form.get("source_note") or ""
    user_note = request.form.get("notes") or ""
    notes = "; ".join(
        note
        for note in (
            "Confirmed from Gainz suggested filed totals review.",
            source_note,
            user_note,
        )
        if note
    )

    transactions.set_tax_year_record(
        year=year,
        reported_proceeds=_money_from_form_or_existing("reported_proceeds", "reported_proceeds", existing_record),
        reported_cost_basis=_money_from_form_or_existing("reported_cost_basis", "reported_cost_basis", existing_record),
        reported_gain_loss=_money_from_form_or_existing("reported_gain_loss", "reported_gain_loss", existing_record),
        tax_paid=_money_from_form_or_existing("tax_paid", "tax_paid", existing_record),
        filing_status=request.form.get("filing_status") or _existing_text_or_form("filing_status", "filing_status", existing_record) or "Filed",
        evidence_reference=source_reference or _existing_text_or_form("evidence_reference", "evidence_reference", existing_record),
        notes=notes,
    )
    transactions.save(description=f"Confirmed suggested filed totals for {year}")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_year=year, saved_suggestion=1))


@blueprint.route('/suggested_totals/research', methods=['POST'])
@login_required
def mark_suggested_filed_totals_needs_research():
    transactions = current_app.config['transactions']
    year = int(request.form.get("year"))
    existing_record = transactions.get_tax_year_record(year)
    source_reference = request.form.get("source_reference") or _existing_text_or_form("evidence_reference", "evidence_reference", existing_record)
    user_note = request.form.get("notes") or "Review source evidence before recording filed totals."

    transactions.set_tax_year_record(
        year=year,
        reported_proceeds=existing_record.get("reported_proceeds") if existing_record else None,
        reported_cost_basis=existing_record.get("reported_cost_basis") if existing_record else None,
        reported_gain_loss=existing_record.get("reported_gain_loss") if existing_record else None,
        tax_paid=existing_record.get("tax_paid") if existing_record else None,
        filing_status="Needs research",
        evidence_reference=source_reference,
        notes=user_note,
    )
    transactions.save(description=f"Marked filed totals for {year} as needs research")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_year=year, saved_suggestion=1))


@blueprint.route('/evidence', methods=['POST'])
@login_required
def save_tax_evidence_record():
    transactions = current_app.config['transactions']
    uploaded_path = _save_uploaded_evidence(request.files.get("evidence_file"))
    reference = uploaded_path or request.form.get("evidence_reference") or ""
    notes = request.form.get("evidence_notes") or ""

    if not reference and not notes:
        return redirect(url_for('tax_filing_review_blueprint.index'))

    _add_tax_evidence_record(
        transactions,
        year=request.form.get("evidence_year"),
        reference=reference,
        evidence_type=request.form.get("evidence_type") or "auto",
        notes=notes,
    )
    transactions.save(description="Added tax evidence inventory item")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_evidence=1))


@blueprint.route('/scan_evidence_folder', methods=['POST'])
@login_required
def scan_tax_evidence_folder():
    transactions = current_app.config['transactions']
    folder_value = request.form.get("evidence_folder") or ""
    if not folder_value.strip():
        return redirect(url_for('tax_filing_review_blueprint.index', saved_evidence=0))

    folder = Path(folder_value)
    recursive = request.form.get("recursive") == "1"

    if not folder.exists() or not folder.is_dir():
        return redirect(url_for('tax_filing_review_blueprint.index', saved_evidence=0))

    paths = folder.rglob("*") if recursive else folder.iterdir()
    added = 0
    for path in sorted(paths):
        if added >= 500:
            break
        if not path.is_file() or path.suffix.lower() not in TAX_EVIDENCE_SCAN_EXTENSIONS:
            continue

        evidence_type = classify_tax_evidence(str(path))
        transactions.set_tax_evidence_record(
            year=infer_tax_evidence_year(path.name, path.parent.name),
            evidence_type=evidence_type,
            evidence_label=path.name,
            evidence_path=str(path),
            notes="Scanned from local evidence folder.",
        )
        added += 1

    if added:
        transactions.save(description=f"Scanned {added} tax evidence item(s)")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_evidence=added))


@blueprint.route('/import_csv', methods=['POST'])
@login_required
def import_filed_totals_csv():
    transactions = current_app.config['transactions']
    file_storage = request.files.get("csv_file")
    if not file_storage or not file_storage.filename:
        return redirect(url_for('tax_filing_review_blueprint.index'))

    try:
        summary = import_tax_total_records(file_storage, transactions, file_storage.filename)
        if summary["imported_count"]:
            transactions.save(description=f"Imported {summary['imported_count']} filed tax total record(s) from CSV")

        return redirect(url_for(
            'tax_filing_review_blueprint.index',
            imported_tax_rows=summary["imported_count"],
            skipped_tax_rows=summary["skipped_count"],
        ))
    except Exception:
        current_app.logger.exception("Error importing filed totals CSV")
        return redirect(url_for('tax_filing_review_blueprint.index', tax_import_error=1))
