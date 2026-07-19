from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_export_routes_do_not_open_browser_submitted_paths():
    text = _read("app/export/routes.py")

    assert 'request.form.get("folder")' not in text
    assert 'request.form.get("path")' not in text
    assert "request.referrer" not in text
    assert "packet_path=request" not in text
    assert "str(exc)" not in text


def test_export_page_uses_output_location_tokens_not_raw_paths():
    route_text = _read("app/export/routes.py")
    script_text = _read("app/base/static/assets/js/custom.js")

    assert 'payload.get("output_dir")' not in route_text
    assert 'request.args.get("output_dir")' not in route_text
    assert 'request.form.get("output_dir")' not in route_text
    assert "'output_dir': $('#export_output_dir').val()" not in script_text
    assert "'output_location': $('#export_output_location').val()" in script_text


def test_tax_evidence_scan_uses_location_tokens_not_raw_folder_paths():
    route_text = _read("app/tax_filing_review/routes.py")
    template_text = _read("app/tax_filing_review/templates/tax_filing_review.html")

    assert 'request.form.get("evidence_folder")' not in route_text
    assert 'name="evidence_folder"' not in template_text
    assert 'name="scan_location"' in template_text


def test_password_reset_script_does_not_create_or_echo_temporary_password():
    text = _read("scripts/reset_admin_password.py")

    assert "--password" not in text
    assert "gainz-local-reset" not in text
    assert "No temporary or default password was created." in text
