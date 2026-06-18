import csv
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from openpyxl import load_workbook

from app.services.audit_packet_service import AuditPacketService
from app.services.import_service import ImportService
from transactions import Transactions
from utils import get_form_8949_report_rows


def empty_transactions():
    transactions = Transactions.__new__(Transactions)
    transactions.revision_num = 0
    transactions.saves = []
    transactions.index = 0
    transactions.conversions = []
    transactions.asset_objects = []
    transactions.import_warnings = []
    transactions.import_warning_reviews = []
    transactions.basis_review_notes = []
    transactions.tax_year_records = []
    transactions.tax_evidence_records = []
    transactions.work_order_reviews = []
    transactions.view = ""
    transactions.transactions = []
    transactions.saved_descriptions = []

    def fake_save(description=None):
        transactions.saved_descriptions.append(description)

    transactions.save = fake_save
    return transactions


def set_expected_holdings(transactions):
    for asset in sorted(transactions.assets):
        expected = 0.0
        for transaction in transactions.transactions:
            if transaction.symbol != asset:
                continue
            if transaction.trans_type in ("buy", "receive"):
                expected += transaction.quantity
            elif transaction.trans_type in ("sell", "send"):
                expected -= transaction.quantity
        transactions.set_holdings(asset, expected)


def normalize_demo_source_paths(transactions):
    for transaction in transactions.transactions:
        source = Path(str(transaction.source))
        try:
            transaction.source = str(source.resolve().relative_to(REPO_ROOT))
        except (OSError, ValueError):
            transaction.source = source.name or str(transaction.source)


def set_synthetic_filed_totals(transactions):
    by_year = {}
    for row in get_form_8949_report_rows(transactions):
        year = int(row["year"])
        totals = by_year.setdefault(
            year,
            {"proceeds": 0.0, "cost_basis": 0.0, "gain_loss": 0.0},
        )
        totals["proceeds"] += float(row["proceeds"])
        totals["cost_basis"] += float(row["cost_basis"])
        totals["gain_loss"] += float(row["gain_loss"])

    for year, totals in sorted(by_year.items()):
        transactions.set_tax_year_record(
            year,
            reported_proceeds=totals["proceeds"],
            reported_cost_basis=totals["cost_basis"],
            reported_gain_loss=totals["gain_loss"],
            tax_paid=max(totals["gain_loss"], 0) * 0.25,
            filing_status="Synthetic demo only",
            evidence_reference=f"Synthetic {year} filed return summary",
            notes="Synthetic public sample record. Not a real tax filing.",
        )
        transactions.set_tax_evidence_record(
            year=year,
            evidence_type="filed_return",
            evidence_label=f"Synthetic {year} filed return summary (reference-only demo)",
            notes="Synthetic reference for the public sample packet. No real evidence file is copied.",
        )


def _replacement_pairs(packet_path):
    home = Path.home()
    pairs = [
        (str(packet_path), "gainz-synthetic-audit-packet-sample"),
        (str(packet_path).replace("\\", "/"), "gainz-synthetic-audit-packet-sample"),
        (str(packet_path.parent), "gainz-synthetic-audit-packet-build"),
        (str(packet_path.parent).replace("\\", "/"), "gainz-synthetic-audit-packet-build"),
        (str(REPO_ROOT), "gainz-demo-repo"),
        (str(REPO_ROOT).replace("\\", "/"), "gainz-demo-repo"),
        (str(home), "<user-home>"),
        (str(home).replace("\\", "/"), "<user-home>"),
    ]
    return pairs + [(old.replace("\\", "\\\\"), new) for old, new in pairs]


def _sanitize_text_file(path, replacements):
    text = path.read_text(encoding="utf-8")
    sanitized = text
    for old, new in replacements:
        sanitized = sanitized.replace(old, new)
    if sanitized != text:
        path.write_text(sanitized, encoding="utf-8")


def _sanitize_workbook(path, replacements):
    workbook = load_workbook(path)
    changed = False
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                value = cell.value
                for old, new in replacements:
                    value = value.replace(old, new)
                if value != cell.value:
                    cell.value = value
                    changed = True
    if changed:
        workbook.save(path)
    workbook.close()
    return changed


def sanitize_public_sample_packet(packet_path, audit_service):
    replacements = _replacement_pairs(packet_path)
    for path in packet_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".csv", ".json", ".md", ".txt"}:
            _sanitize_text_file(path, replacements)
        elif path.suffix.lower() == ".xlsx":
            _sanitize_workbook(path, replacements)

    manifest_path = packet_path / "03_manifests" / "evidence_manifest.csv"
    with open(manifest_path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        if row["category"] != "generated_report":
            continue
        report_path = packet_path / row["packet_relative_path"]
        report_hash = audit_service._sha256(report_path)
        row["source_path"] = row["packet_relative_path"]
        row["source_sha256"] = report_hash
        row["packet_sha256"] = report_hash
        row["size_bytes"] = str(report_path.stat().st_size)

    with open(manifest_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    audit_service._write_inventory(packet_path)


def build_packet_zip():
    downloads_dir = REPO_ROOT / "docs" / "assets" / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    output_zip = downloads_dir / "gainz-synthetic-audit-packet-sample.zip"

    transactions = empty_transactions()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        ImportService(temp_path / "uploads").import_demo_data(transactions, repo_root=REPO_ROOT)
        transactions.auto_link(asset=None, algo="fifo")
        normalize_demo_source_paths(transactions)
        set_expected_holdings(transactions)
        set_synthetic_filed_totals(transactions)

        packet_root = temp_path / "packets"
        export_root = temp_path / "exports"
        audit_service = AuditPacketService(packet_root, export_root)
        packet_path = Path(audit_service.create_packet(transactions))
        sanitize_public_sample_packet(packet_path, audit_service)

        staged_zip = temp_path / output_zip.name
        with zipfile.ZipFile(staged_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(packet_path.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(packet_path))

        shutil.copy2(staged_zip, output_zip)

    return output_zip


if __name__ == "__main__":
    print(build_packet_zip())
