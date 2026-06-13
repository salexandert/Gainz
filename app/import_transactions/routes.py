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

import dateutil.parser
import os
from collections import Counter
from datetime import datetime

from flask import Blueprint, request
from transactions import Transactions
from app.services.import_service import ImportService

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

    for transaction in getattr(transactions, "transactions", []):
        source = getattr(transaction, "source", "") or "Manual / Unknown"
        source_counter[source] += 1
        type_counter[getattr(transaction, "trans_type", "unknown")] += 1

    sources = []
    for source, count in source_counter.most_common():
        exists = os.path.exists(str(source))
        is_gainz_source = (
            str(source).startswith("Gainz App")
            or "Converted in Gainz App" in str(source)
            or "Reclassified in Gainz App" in str(source)
        )
        sources.append({
            "source": source,
            "name": os.path.basename(str(source)) if source != "Manual / Unknown" else source,
            "count": count,
            "status": "Available" if exists else "Generated in Gainz" if is_gainz_source else "Not found",
            "is_file": exists,
            "is_gainz_source": is_gainz_source,
        })

    return {
        "transaction_count": len(getattr(transactions, "transactions", [])),
        "asset_count": len(getattr(transactions, "assets", set())),
        "link_count": len(getattr(transactions, "links", set())),
        "source_count": len(sources),
        "sources": sources,
        "type_counts": {
            "buy": type_counter.get("buy", 0),
            "sell": type_counter.get("sell", 0),
            "send": type_counter.get("send", 0),
            "receive": type_counter.get("receive", 0),
        },
        "import_warnings": getattr(transactions, "import_warnings", []) or [],
    }


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
                result = ImportService(current_app.config['UPLOAD_FOLDER']).import_upload(
                    file,
                    transactions,
                    review_columns=review_columns,
                )
                if result.get("mapping_required"):
                    session["pending_import_file_path"] = result["file_path"]
                return jsonify(result)

        # Current holdings
        if current_holdings.validate_on_submit():
            pass

        if manual_trans.validate_on_submit():
            if manual_trans.type.data == 'buy':
                trans = Buy(
                    trans_type=manual_trans.type.data,
                    time_stamp=manual_trans.timestamp.data,
                    quantity=float(manual_trans.quantity.data),
                    usd_spot=float(manual_trans.usd_spot.data),
                    symbol=manual_trans.symbol.data.upper(),
                    source="Gainz App Manual Add"
                )
            else:
                trans = Sell(
                    trans_type=manual_trans.type.data,
                    time_stamp=manual_trans.timestamp.data,
                    quantity=float(manual_trans.quantity.data),
                    usd_spot=float(manual_trans.usd_spot.data),
                    symbol=manual_trans.symbol.data.upper(),
                    source="Gainz App Manual Add"
                )

            transactions.transactions.append(trans)
            transactions.save(description="Manually Added Transaction")
            return redirect(
                url_for(
                    'import_transactions_blueprint.import_wizard',
                    manual_added=trans.symbol,
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
    result = ImportService(current_app.config['UPLOAD_FOLDER']).import_mapped_file(
        file_path,
        transactions,
        header_row=header_row,
        column_mapping=column_mapping,
        data_start_row=data_start_row,
    )

    if not result.get("mapping_required"):
        session.pop("pending_import_file_path", None)

    return jsonify(result)


@blueprint.route('/demo', methods=['POST'])
@login_required
def import_demo_data():
    transactions = current_app.config['transactions']
    result = ImportService(current_app.config['UPLOAD_FOLDER']).import_demo_data(
        transactions,
        repo_root=current_app.root_path + "/..",
    )
    return jsonify(result)


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


