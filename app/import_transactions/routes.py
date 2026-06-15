from . import blueprint
from flask import Flask, render_template, session, redirect, url_for, session, request, current_app
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from wtforms import (SelectField,StringField,
                     SubmitField, DecimalField, DateField)

from wtforms.fields import DateField
from transaction import Buy, Sell
import json
from flask import jsonify
from conversion import Conversion

from wtforms.fields import DateTimeLocalField
from utils import *

import os
from collections import Counter
from datetime import date, datetime, time

from flask import Blueprint, request
from transactions import Transactions
from date_parsing import parse_gainz_datetime
from app.services.import_service import ImportService
from app.services.import_warning_service import (
    clear_import_warnings_for_source,
    import_warning_review_rows,
    unresolved_import_warning_rows,
)
from app.services.source_overlap_service import detect_source_overlaps, sources_with_overlaps
from runtime_paths import resource_dir

import_transactions_bp = Blueprint('import_transactions', __name__)

class ManualTransaction(FlaskForm):
    '''
    Manual Transaction values
    '''
    timestamp = DateTimeLocalField('Timestamp', format='%Y-%m-%dT%H:%M')
    type  = SelectField(u'Type', choices=[('buy', 'Buy'), ('sell', 'Sell')])
    symbol = StringField('Crypto Symbol')
    quantity = DecimalField('Quantity', rounding=None)
    usd_spot = DecimalField('USD Spot', rounding=None)

    submit = SubmitField('Submit')


class CurrentHoldings(FlaskForm):
    symbol = StringField('Crypto Symbol')
    quantity = DecimalField('Quantity', rounding=None)

    submit = SubmitField('Submit')


MANUAL_TRANSACTION_SOURCE = "Gainz App Manual Add"


def _safe_filename(value):
    return os.path.basename(str(value or "").replace("\\", "/"))


def _manual_row_is_blank(row):
    return not any(
        str(row.get(field, "") or "").strip()
        for field in ("timestamp", "symbol", "quantity", "usd_spot")
    )


def _manual_transaction_from_values(row, row_number=None):
    prefix = f"Row {row_number}: " if row_number else ""
    trans_type = str(row.get("type", "") or "").strip().lower()
    timestamp = str(row.get("timestamp", "") or "").strip()
    symbol = str(row.get("symbol", "") or "").strip().upper()
    quantity = str(row.get("quantity", "") or "").strip()
    usd_spot = str(row.get("usd_spot", "") or "").strip()

    if trans_type not in ("buy", "sell"):
        raise ValueError(f"{prefix}choose Buy or Sell.")

    missing = [
        label
        for field, label in (
            ("timestamp", "Timestamp"),
            ("symbol", "Crypto Symbol"),
            ("quantity", "Quantity"),
            ("usd_spot", "USD Spot"),
        )
        if not str(row.get(field, "") or "").strip()
    ]
    if missing:
        raise ValueError(f"{prefix}complete {', '.join(missing)}.")

    try:
        parsed_timestamp = parse_gainz_datetime(timestamp)
    except (TypeError, ValueError):
        raise ValueError(f"{prefix}enter a valid timestamp.")

    try:
        parsed_quantity = float(quantity)
        parsed_usd_spot = float(usd_spot)
    except (TypeError, ValueError):
        raise ValueError(f"{prefix}quantity and USD spot must be numbers.")

    if parsed_quantity <= 0:
        raise ValueError(f"{prefix}quantity must be greater than zero.")

    if parsed_usd_spot < 0:
        raise ValueError(f"{prefix}USD spot cannot be negative.")

    transaction_class = Buy if trans_type == "buy" else Sell
    return transaction_class(
        trans_type=trans_type,
        time_stamp=parsed_timestamp,
        quantity=parsed_quantity,
        usd_spot=parsed_usd_spot,
        symbol=symbol,
        source=MANUAL_TRANSACTION_SOURCE,
    )


def _manual_batch_rows(form_data):
    types = form_data.getlist("manual_type[]")
    timestamps = form_data.getlist("manual_timestamp[]")
    symbols = form_data.getlist("manual_symbol[]")
    quantities = form_data.getlist("manual_quantity[]")
    usd_spots = form_data.getlist("manual_usd_spot[]")
    row_count = max(
        len(types),
        len(timestamps),
        len(symbols),
        len(quantities),
        len(usd_spots),
    )
    rows = []

    for index in range(row_count):
        rows.append({
            "row_number": index + 1,
            "type": (types + [""] * row_count)[index],
            "timestamp": (timestamps + [""] * row_count)[index],
            "symbol": (symbols + [""] * row_count)[index],
            "quantity": (quantities + [""] * row_count)[index],
            "usd_spot": (usd_spots + [""] * row_count)[index],
        })

    return rows


def _format_modified_time(timestamp):
    if not timestamp:
        return "N/A"

    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %I:%M %p")


def _current_save_summary(transactions, refresh=False):
    saves = transactions.load_saves() if refresh else list(getattr(transactions, "saves", []) or [])
    current_view = getattr(transactions, "view", "") or ""
    current_save = next((save for save in saves if save["value"] == current_view), None)

    if current_save is None and saves:
        current_save = saves[-1]

    revision = getattr(transactions, "revision_num", None)
    if (revision is None or revision == 0) and current_save:
        revision = current_save.get("revision_num") or revision

    return {
        "revision": revision or 0,
        "save_count": len(saves),
        "current_file": current_save["value"] if current_save else "Unsaved session",
        "current_name": os.path.basename(current_save["value"]) if current_save else "Unsaved session",
        "current_description": current_save["description"] if current_save else "",
        "current_modified": _format_modified_time(current_save["modified_time"]) if current_save else "N/A",
        "recent_saves": [
            {
                "file": save["value"],
                "name": os.path.basename(save["value"]),
                "description": save["description"] or "",
                "revision": save.get("revision_num") or "",
                "modified": _format_modified_time(save.get("modified_time")),
            }
            for save in reversed(saves[-5:])
        ],
    }


def _data_source_summary(transactions):
    source_counter = Counter()
    type_counter = Counter()
    source_ranges = {}

    for transaction in getattr(transactions, "transactions", []):
        source = getattr(transaction, "source", "") or "Manual / Unknown"
        source_counter[source] += 1
        type_counter[getattr(transaction, "trans_type", "unknown")] += 1
        timestamp = getattr(transaction, "time_stamp", None)
        if timestamp is not None:
            if hasattr(timestamp, "to_pydatetime"):
                timestamp = timestamp.to_pydatetime()
            if isinstance(timestamp, date) and not isinstance(timestamp, datetime):
                timestamp = datetime.combine(timestamp, time.min)
            if hasattr(timestamp, "replace"):
                try:
                    timestamp = timestamp.replace(tzinfo=None)
                except TypeError:
                    pass
            source_ranges.setdefault(source, []).append(timestamp)

    source_overlaps = detect_source_overlaps(transactions)
    overlapped_sources = sources_with_overlaps(source_overlaps)
    sources = []
    for source, count in source_counter.most_common():
        exists = os.path.exists(str(source))
        is_gainz_source = (
            str(source).startswith("Gainz App")
            or "Converted in Gainz App" in str(source)
            or "Reclassified in Gainz App" in str(source)
        )
        timestamps = source_ranges.get(source, [])
        date_range = "N/A"
        if timestamps:
            first = min(timestamps)
            last = max(timestamps)
            if hasattr(first, "strftime") and hasattr(last, "strftime"):
                date_range = f"{first.strftime('%Y-%m-%d')} to {last.strftime('%Y-%m-%d')}"
            else:
                date_range = f"{first} to {last}"
        sources.append({
            "source": source,
            "name": os.path.basename(str(source)) if source != "Manual / Unknown" else source,
            "count": count,
            "status": (
                "Potential overlap"
                if source in overlapped_sources
                else "Available" if exists else "Generated in Gainz" if is_gainz_source else "Not found"
            ),
            "is_file": exists,
            "is_gainz_source": is_gainz_source,
            "has_overlap": source in overlapped_sources,
            "date_range": date_range,
        })

    import_warnings = getattr(transactions, "import_warnings", []) or []
    warning_rows = import_warning_review_rows(import_warnings, transactions=transactions)

    return {
        "transaction_count": len(getattr(transactions, "transactions", [])),
        "asset_count": len(getattr(transactions, "assets", set())),
        "link_count": len(getattr(transactions, "links", set())),
        "source_count": len(sources),
        "source_overlaps": source_overlaps,
        "source_overlap_count": len(source_overlaps),
        "sources": sources,
        "type_counts": {
            "buy": type_counter.get("buy", 0),
            "sell": type_counter.get("sell", 0),
            "send": type_counter.get("send", 0),
            "receive": type_counter.get("receive", 0),
        },
        "import_warnings": import_warnings,
        "import_warning_rows": warning_rows,
        "unresolved_import_warning_count": len(unresolved_import_warning_rows(transactions)),
    }


def _public_import_result(result):
    public_result = dict(result or {})
    file_path = public_result.pop("file_path", None)
    if file_path and "filename" not in public_result:
        public_result["filename"] = _safe_filename(file_path)

    if "files" in public_result:
        public_files = []
        for item in public_result.get("files", []) or []:
            public_item = dict(item)
            item_path = public_item.pop("file_path", None)
            if item_path and "filename" not in public_item:
                public_item["filename"] = _safe_filename(item_path)
            public_files.append(public_item)
        public_result["files"] = public_files

    if public_result.get("mapping_required"):
        public_result["warning_rows"] = []
    else:
        public_result["warning_rows"] = import_warning_review_rows(public_result.get("warnings", []))

    return public_result


def _public_import_response(transactions, result):
    public_result = _public_import_result(result)
    public_result["data_summary"] = _data_source_summary(transactions)
    return public_result


def _import_error_response(action):
    current_app.logger.exception("Import failed while handling %s.", action)
    return jsonify({
        "error": "Gainz could not complete that import. Review the file format and try again."
    }), 400


def _remove_data_source(transactions, source):
    source = str(source or "")
    original_transactions = list(getattr(transactions, "transactions", []))
    removed_transactions = [
        transaction
        for transaction in original_transactions
        if str(getattr(transaction, "source", "") or "Manual / Unknown") == source
    ]

    if not removed_transactions:
        return {
            "removed_count": 0,
            "source": source,
            "source_name": os.path.basename(source) or source or "Manual / Unknown",
        }

    removed_ids = {id(transaction) for transaction in removed_transactions}
    removed_links = {
        link
        for transaction in removed_transactions
        for link in getattr(transaction, "links", [])
    }

    remaining_transactions = [
        transaction
        for transaction in original_transactions
        if id(transaction) not in removed_ids
    ]

    for transaction in remaining_transactions:
        transaction.links = [
            link
            for link in getattr(transaction, "links", [])
            if (
                link not in removed_links
                and id(getattr(link, "buy", None)) not in removed_ids
                and id(getattr(link, "sell", None)) not in removed_ids
            )
        ]
        transaction.update_linked_transactions()
        transaction.set_multi_link()

    transactions.transactions = remaining_transactions
    transactions.conversions = [
        conversion
        for conversion in getattr(transactions, "conversions", [])
        if str(getattr(conversion, "source", "") or "") != source
    ]
    clear_import_warnings_for_source(transactions, source)

    return {
        "removed_count": len(removed_transactions),
        "source": source,
        "source_name": os.path.basename(source) or source or "Manual / Unknown",
    }


@blueprint.route('/', methods=['GET', 'POST'])
@login_required
def import_wizard():
    transactions = current_app.config['transactions']
    manual_trans = ManualTransaction()
    current_holdings = CurrentHoldings()

    if 'current_holdings' not in session:
        session['current_holdings'] = []

    # if file is uploaded add new transactions
    if request.method == 'POST':
        # Import from CSV File
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                review_columns = request.form.get("review_columns") in ("1", "true", "on", "yes")
                try:
                    result = ImportService(current_app.config['UPLOAD_FOLDER']).import_upload(
                        file,
                        transactions,
                        review_columns=review_columns,
                    )
                except Exception:
                    return _import_error_response("uploaded CSV")
                if result.get("mapping_required"):
                    session["pending_import_file_path"] = result["file_path"]
                return jsonify(_public_import_response(transactions, result))

        # Current holdings
        if current_holdings.validate_on_submit():
            pass

        if "manual_batch_submit" in request.form:
            rows = [
                row
                for row in _manual_batch_rows(request.form)
                if not _manual_row_is_blank(row)
            ]

            if not rows:
                return redirect(
                    url_for(
                        'import_transactions_blueprint.import_wizard',
                        manual_error="Enter at least one manual transaction.",
                    ) + '#manual-transactions'
                )

            try:
                manual_transactions = [
                    _manual_transaction_from_values(row, row.get("row_number"))
                    for row in rows
                ]
            except ValueError as exc:
                return redirect(
                    url_for(
                        'import_transactions_blueprint.import_wizard',
                        manual_error=str(exc),
                    ) + '#manual-transactions'
                )

            transactions.transactions.extend(manual_transactions)
            count = len(manual_transactions)
            transactions.save(
                description=f"Manually Added {count} Transaction{'s' if count != 1 else ''}"
            )
            return redirect(
                url_for(
                    'import_transactions_blueprint.import_wizard',
                    manual_added=count,
                ) + '#manual-transactions'
            )

        if manual_trans.validate_on_submit():
            trans = _manual_transaction_from_values({
                "type": manual_trans.type.data,
                "timestamp": manual_trans.timestamp.data,
                "symbol": manual_trans.symbol.data,
                "quantity": manual_trans.quantity.data,
                "usd_spot": manual_trans.usd_spot.data,
            })

            transactions.transactions.append(trans)
            transactions.save(description="Manually Added Transaction")
            return redirect(
                url_for(
                    'import_transactions_blueprint.import_wizard',
                    manual_added=1,
                ) + '#manual-transactions'
            )

    return render_template(
        'import_transactions.html',
        manual_trans=manual_trans,
        current_holdings=current_holdings,
        save_summary=_current_save_summary(transactions),
        data_summary=_data_source_summary(transactions),
    )


@blueprint.route('/mapping_preview', methods=['POST'])
@login_required
def mapping_preview():
    file_path = session.get("pending_import_file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Upload a CSV before mapping columns."}), 400

    data = request.get_json(silent=True) or {}
    header_row = data.get("header_row") or 1
    data_start_row = data.get("data_start_row")
    analysis = ImportService(current_app.config['UPLOAD_FOLDER']).analyze_import_file(
        file_path,
        header_row=header_row,
        data_start_row=data_start_row,
    )
    return jsonify({"mapping": analysis})


@blueprint.route('/mapped_import', methods=['POST'])
@login_required
def mapped_import():
    file_path = session.get("pending_import_file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Upload a CSV before mapping columns."}), 400

    data = request.get_json(silent=True) or {}
    header_row = data.get("header_row") or 1
    data_start_row = data.get("data_start_row")
    column_mapping = data.get("column_mapping") or {}

    transactions = current_app.config['transactions']
    try:
        result = ImportService(current_app.config['UPLOAD_FOLDER']).import_mapped_file(
            file_path,
            transactions,
            header_row=header_row,
            column_mapping=column_mapping,
            data_start_row=data_start_row,
        )
    except Exception:
        return _import_error_response("mapped CSV")

    if not result.get("mapping_required"):
        session.pop("pending_import_file_path", None)

    return jsonify(_public_import_response(transactions, result))


@blueprint.route('/demo', methods=['POST'])
@login_required
def import_demo_data():
    transactions = current_app.config['transactions']
    try:
        result = ImportService(current_app.config['UPLOAD_FOLDER']).import_demo_data(
            transactions,
            repo_root=resource_dir(),
        )
    except Exception:
        return _import_error_response("demo data")
    return jsonify(_public_import_response(transactions, result))


@blueprint.route('/remove_source', methods=['POST'])
@login_required
def remove_source():
    data = request.get_json(silent=True) or {}
    source = data.get("source")

    if not source:
        return jsonify({"error": "Choose a data source to remove."}), 400

    transactions = current_app.config['transactions']
    result = _remove_data_source(transactions, source)

    if result["removed_count"] == 0:
        return jsonify({"error": "No transactions matched that data source."}), 404

    save_path = transactions.save(
        description=f"Removed data source {result['source_name']}"
    )

    return jsonify({
        "message": (
            f"Removed {result['removed_count']} transaction"
            f"{'' if result['removed_count'] == 1 else 's'} from {result['source_name']} "
            "and saved a new revision. Prior revisions remain available in History."
        ),
        "removed_count": result["removed_count"],
        "source": result["source"],
        "source_name": result["source_name"],
        "save_path": save_path,
        "save_summary": _current_save_summary(transactions, refresh=True),
        "data_summary": _data_source_summary(transactions),
    })


@blueprint.route('/import_warning_review', methods=['POST'])
@login_required
def import_warning_review():
    data = request.get_json(silent=True) or {}
    warning = str(data.get("warning") or "")
    decision = str(data.get("decision") or "")
    note = str(data.get("note") or "")

    if not warning:
        return jsonify({"error": "Choose an import warning to review."}), 400

    transactions = current_app.config['transactions']
    if warning not in (getattr(transactions, "import_warnings", []) or []):
        return jsonify({"error": "That warning is not part of the current save."}), 404

    transactions.set_import_warning_review(warning, decision=decision, note=note)
    save_path = transactions.save(description="Reviewed import warning")

    return jsonify({
        "message": "Import warning review decision saved.",
        "save_path": save_path,
        "data_summary": _data_source_summary(transactions),
        "save_summary": _current_save_summary(transactions, refresh=True),
    })


