import os
from fnmatch import fnmatch
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
from app.services.auto_link_service import AutoLinkService

from . import blueprint


TAX_EVIDENCE_SCAN_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".txt", ".png", ".jpg", ".jpeg"}
DEFAULT_EVIDENCE_SCAN_EXCLUDE_FOLDERS = [
    "90_Gainz_Product_Review_Archive",
    "Gainz_v*_validation_*",
    "gainz_audit_packet_*",
    "downloads",
    "package",
    "exports",
    "audit_packets",
    "uploads",
]
EVIDENCE_SCAN_PRESETS = {
    "crypto_tax_evidence": {
        "label": "Crypto tax evidence only",
        "extensions": {".pdf", ".csv", ".xlsx", ".xls"},
        "include_keywords": [
            "crypto",
            "bitcoin",
            "btc",
            "coinbase",
            "cash app",
            "8949",
            "schedule d",
            "capital gain",
            "gain loss",
            "tax workbook",
        ],
        "exclude_keywords": ["w2", "1098", "1099-int", "mortgage", "paystub"],
    },
    "filed_returns": {
        "label": "Filed returns only",
        "extensions": {".pdf"},
        "include_keywords": ["1040", "return", "filed", "form 8949", "schedule d"],
        "exclude_keywords": ["estimate", "worksheet", "workbook"],
    },
    "payment_receipts": {
        "label": "Payment receipts only",
        "extensions": {".pdf", ".txt", ".png", ".jpg", ".jpeg"},
        "include_keywords": ["payment", "receipt", "confirmation", "direct pay", "eftps", "paid"],
        "exclude_keywords": ["worksheet", "workbook"],
    },
    "transaction_csvs": {
        "label": "Transaction CSVs only",
        "extensions": {".csv"},
        "include_keywords": ["coinbase", "cash app", "gdax", "transaction", "trades", "fills", "tax"],
        "exclude_keywords": [],
    },
}


def _detected_tax_folder():
    candidate = Path.home() / "OneDrive" / "Taxes"
    return str(candidate) if candidate.exists() and candidate.is_dir() else ""


def _scan_location_choices():
    choices = {
        "uploaded_evidence": str(_tax_evidence_upload_dir()),
    }
    detected_tax_folder = _detected_tax_folder()
    if detected_tax_folder:
        choices["detected_taxes"] = detected_tax_folder
    return choices


def _scan_folder_for_location():
    scan_location = (request.form.get("scan_location") or "").strip()
    folder = _scan_location_choices().get(scan_location) or _detected_tax_folder()
    if not folder:
        folder = str(_tax_evidence_upload_dir())
    return Path(folder).resolve()


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


def _split_filter_values(value):
    raw_values = value if isinstance(value, list) else [value]
    values = []
    for raw_value in raw_values:
        for part in str(raw_value or "").replace(";", ",").replace("\n", ",").split(","):
            part = part.strip().lower()
            if part:
                values.append(part)
    return values


def _scan_year_filters():
    years = set()
    for value in _split_filter_values(request.form.get("evidence_years") or ""):
        try:
            year = int(value)
        except ValueError:
            continue
        if 2009 <= year <= 2100:
            years.add(year)
    return years


def _scan_extension_filters():
    preset = EVIDENCE_SCAN_PRESETS.get(request.form.get("scan_preset") or "")
    if preset:
        return set(preset["extensions"])

    requested = _split_filter_values(request.form.getlist("evidence_file_types"))
    if not requested:
        return TAX_EVIDENCE_SCAN_EXTENSIONS

    extensions = set()
    for value in requested:
        extension = value if value.startswith(".") else f".{value}"
        if extension in TAX_EVIDENCE_SCAN_EXTENSIONS:
            extensions.add(extension)

    return extensions or TAX_EVIDENCE_SCAN_EXTENSIONS


def _scan_keyword_filters(form_name, preset_key):
    preset = EVIDENCE_SCAN_PRESETS.get(request.form.get("scan_preset") or "")
    values = []
    if preset:
        values.extend(preset.get(preset_key, []))
    values.extend(_split_filter_values(request.form.get(form_name) or ""))
    deduped = []
    for value in values:
        normalized = str(value or "").strip().lower()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def _path_matches_scan_filters(path, years, include_keywords, exclude_keywords):
    inferred_year = infer_tax_evidence_year(path.name, path.parent.name)
    if years and inferred_year not in years:
        return False

    searchable_text = str(path).lower()
    if include_keywords and not any(keyword in searchable_text for keyword in include_keywords):
        return False

    if exclude_keywords and any(keyword in searchable_text for keyword in exclude_keywords):
        return False

    return True


def _default_excluded_scan_folder(path):
    for part in Path(path).parts:
        normalized_part = str(part).strip().lower()
        for pattern in DEFAULT_EVIDENCE_SCAN_EXCLUDE_FOLDERS:
            if fnmatch(normalized_part, pattern.lower()):
                return pattern
    return ""


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


def _add_tax_evidence_record(
    transactions,
    year,
    reference,
    evidence_type,
    notes,
    copy_to_packet=False,
    trusted_path=False,
):
    evidence_type = classify_tax_evidence(reference, notes, evidence_type)
    record_year = _optional_year(year, reference, notes)
    label = os.path.basename(str(reference)) if reference else tax_evidence_type_label(evidence_type)
    evidence_path = reference if trusted_path else ""

    return transactions.set_tax_evidence_record(
        year=record_year,
        evidence_type=evidence_type,
        evidence_label=label,
        evidence_path=evidence_path,
        copy_to_packet=bool(copy_to_packet and evidence_path),
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
        evidence_scan_presets=[
            {"value": value, "label": preset["label"]}
            for value, preset in EVIDENCE_SCAN_PRESETS.items()
        ],
        scan_locations=[
            {
                "value": value,
                "label": {
                    "detected_taxes": "Detected Taxes folder",
                    "uploaded_evidence": "Gainz uploaded evidence folder",
                }.get(value, value),
                "path": path,
                "selected": value == "detected_taxes",
            }
            for value, path in _scan_location_choices().items()
        ],
        available_years=_available_years(alignment),
        saved_year=request.args.get("saved_year"),
        saved_evidence=request.args.get("saved_evidence"),
        saved_suggestion=request.args.get("saved_suggestion"),
        research_year=request.args.get("research_year"),
        imported_tax_rows=request.args.get("imported_tax_rows"),
        skipped_tax_rows=request.args.get("skipped_tax_rows"),
        tax_import_error=request.args.get("tax_import_error"),
        skipped_evidence_folders=request.args.get("skipped_evidence_folders"),
        default_evidence_scan_exclude_folders=DEFAULT_EVIDENCE_SCAN_EXCLUDE_FOLDERS,
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
    AutoLinkService().ensure_default_fifo_links(
        transactions,
        reason="filed tax totals update",
    )

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
    AutoLinkService().ensure_default_fifo_links(
        transactions,
        reason="filed tax totals update",
    )

    return redirect(url_for('tax_filing_review_blueprint.index', saved_year=year, saved_suggestion=1))


@blueprint.route('/suggested_totals/research', methods=['POST'])
@login_required
def mark_suggested_filed_totals_needs_research():
    transactions = current_app.config['transactions']
    year = int(request.form.get("year"))
    existing_record = transactions.get_tax_year_record(year)
    source_reference = request.form.get("source_reference") or _existing_text_or_form("evidence_reference", "evidence_reference", existing_record)
    user_note = request.form.get("notes") or "Review source evidence before recording filed totals."
    source_label = os.path.basename(str(source_reference)) if source_reference else f"{year} suggested filed totals"
    evidence_label = f"{source_label} - filed totals need research"
    notes = "; ".join(
        note
        for note in (
            "Suggested filed totals marked Needs Research. No filed totals were recorded from this suggestion.",
            user_note,
        )
        if note
    )

    transactions.set_tax_evidence_record(
        year=year,
        evidence_type=classify_tax_evidence(source_reference, notes),
        evidence_label=evidence_label,
        evidence_path=source_reference if source_reference and os.path.exists(source_reference) else "",
        copy_to_packet=False,
        notes=notes,
    )
    transactions.save(description=f"Marked suggested filed totals for {year} as needs research")

    return redirect(url_for('tax_filing_review_blueprint.index', research_year=year, saved_suggestion=1))


@blueprint.route('/evidence', methods=['POST'])
@login_required
def save_tax_evidence_record():
    transactions = current_app.config['transactions']
    uploaded_path = _save_uploaded_evidence(request.files.get("evidence_file"))
    reference = uploaded_path or request.form.get("evidence_reference") or ""
    notes = request.form.get("evidence_notes") or ""
    copy_to_packet = request.form.get("copy_to_packet") == "1"

    if not reference and not notes:
        return redirect(url_for('tax_filing_review_blueprint.index'))

    _add_tax_evidence_record(
        transactions,
        year=request.form.get("evidence_year"),
        reference=reference,
        evidence_type=request.form.get("evidence_type") or "auto",
        copy_to_packet=copy_to_packet,
        notes=notes,
        trusted_path=bool(uploaded_path),
    )
    transactions.save(description="Added tax evidence inventory item")

    return redirect(url_for('tax_filing_review_blueprint.index', saved_evidence=1))


@blueprint.route('/scan_evidence_folder', methods=['POST'])
@login_required
def scan_tax_evidence_folder():
    transactions = current_app.config['transactions']
    folder = _scan_folder_for_location()
    recursive = request.form.get("recursive") == "1"
    scan_preset = request.form.get("scan_preset") or ""
    scan_preset_label = EVIDENCE_SCAN_PRESETS.get(scan_preset, {}).get("label", "")
    year_filters = _scan_year_filters()
    extension_filters = _scan_extension_filters()
    include_keywords = _scan_keyword_filters("include_keywords", "include_keywords")
    exclude_keywords = _scan_keyword_filters("exclude_keywords", "exclude_keywords")
    copy_scanned_evidence = request.form.get("copy_scanned_evidence") == "1"

    if not folder.exists() or not folder.is_dir():
        return redirect(url_for('tax_filing_review_blueprint.index', saved_evidence=0))

    paths = folder.rglob("*") if recursive else folder.iterdir()
    added = 0
    skipped_default_folders = set()
    for path in sorted(paths):
        if added >= 500:
            break
        excluded_folder = _default_excluded_scan_folder(path)
        if excluded_folder:
            skipped_default_folders.add(excluded_folder)
            continue
        if not path.is_file() or path.suffix.lower() not in extension_filters:
            continue
        if not _path_matches_scan_filters(path, year_filters, include_keywords, exclude_keywords):
            continue

        evidence_type = classify_tax_evidence(str(path))
        transactions.set_tax_evidence_record(
            year=infer_tax_evidence_year(path.name, path.parent.name),
            evidence_type=evidence_type,
            evidence_label=path.name,
            evidence_path=str(path),
            copy_to_packet=copy_scanned_evidence,
            notes=(
                (
                    f"Scanned from local evidence folder using preset: {scan_preset_label}. "
                    if scan_preset_label
                    else "Scanned from local evidence folder. "
                )
                + "Reference only unless marked for packet copy."
            ),
        )
        added += 1

    if added:
        transactions.save(description=f"Scanned {added} tax evidence item(s)")

    return redirect(url_for(
        'tax_filing_review_blueprint.index',
        saved_evidence=added,
        skipped_evidence_folders=len(skipped_default_folders),
    ))


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
            AutoLinkService().ensure_default_fifo_links(
                transactions,
                reason="filed tax totals import",
            )

        return redirect(url_for(
            'tax_filing_review_blueprint.index',
            imported_tax_rows=summary["imported_count"],
            skipped_tax_rows=summary["skipped_count"],
        ))
    except Exception:
        current_app.logger.exception("Error importing filed totals CSV")
        return redirect(url_for('tax_filing_review_blueprint.index', tax_import_error=1))
