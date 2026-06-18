import os
import subprocess
import sys
from pathlib import Path

from flask import current_app, redirect, render_template, request, url_for
from flask_login import login_required

from runtime_paths import data_dir

from . import blueprint


def _path_for_display(path):
    return str(Path(path).expanduser().resolve())


def _local_storage_rows():
    return [
        {
            "label": "Local data folder",
            "path": _path_for_display(data_dir()),
            "detail": "Runtime data location for packaged or source-run Gainz.",
        },
        {
            "label": "Database",
            "path": _path_for_display(Path(current_app.config["INSTANCE_PATH"]) / "database.db"),
            "detail": "Local users and app metadata. The UI password is hashed here.",
        },
        {
            "label": "Imported file copies",
            "path": _path_for_display(current_app.config["UPLOAD_FOLDER"]),
            "detail": "CSV uploads copied for local import review.",
        },
        {
            "label": "Revision saves",
            "path": _path_for_display(data_dir() / "saves"),
            "detail": "Human-readable xlsx save revisions.",
        },
        {
            "label": "Workbook exports",
            "path": _path_for_display(current_app.config["EXPORT_FOLDER"]),
            "detail": "Generated Excel workbooks.",
        },
        {
            "label": "Audit packets",
            "path": _path_for_display(current_app.config["AUDIT_PACKET_FOLDER"]),
            "detail": "Generated packet folders, reports, manifests, and selected source copies.",
        },
    ]


def _open_folder(path):
    path = Path(path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])


@blueprint.route('/', methods=['GET'])
@login_required
def index():
    return render_template(
        'privacy.html',
        storage_rows=_local_storage_rows(),
        opened=request.args.get("opened"),
    )


@blueprint.route('/open_data_folder', methods=['POST'])
@login_required
def open_data_folder():
    _open_folder(data_dir())
    return redirect(url_for('privacy_blueprint.index', opened=1))
