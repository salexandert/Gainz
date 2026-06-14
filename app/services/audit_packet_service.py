import csv
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from app.services.export_service import ExportService
from app.services.import_warning_service import import_warning_review_rows
from utils import (
    FORM_8949_COLUMNS,
    format_quantity,
    get_audit_readiness_summary,
    get_current_holdings_lots,
    get_form_8949_report_rows,
    get_form_8949_totals,
    get_missing_basis_review_rows,
    get_multi_asset_holdings_reconciliation_table_data,
    get_tax_filing_alignment_summary,
)


class AuditPacketService:
    def __init__(self, packet_root, export_folder):
        self.packet_root = Path(packet_root)
        self.export_folder = export_folder

    def create_packet(self, transactions):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        packet_dir = self.packet_root / f"gainz_audit_packet_{timestamp}"
        packet_dir.mkdir(parents=True, exist_ok=False)

        for folder in (
            "00_memos",
            "01_reports",
            "02_source_files",
            "03_manifests",
        ):
            (packet_dir / folder).mkdir(parents=True, exist_ok=True)

        manifest_rows = []

        report_path = ExportService(self.export_folder).export_to_excel(transactions)
        report_dest = packet_dir / "01_reports" / Path(report_path).name
        shutil.copy2(report_path, report_dest)
        manifest_rows.append(
            self._manifest_row(
                source_path=report_path,
                packet_path=report_dest,
                packet_dir=packet_dir,
                category="generated_report",
                role="Gainz Excel export generated for this audit packet",
                status="GENERATED",
            )
        )

        for source in self._source_paths(transactions):
            source_path = Path(source)
            if not source_path.exists() or not source_path.is_file():
                manifest_rows.append(
                    {
                        "category": "source_file",
                        "role": "Transaction source referenced by imported data but unavailable on disk",
                        "status": "MISSING",
                        "source_path": str(source_path),
                        "packet_relative_path": "",
                        "source_sha256": "",
                        "packet_sha256": "",
                        "size_bytes": "",
                        "last_write_time": "",
                    }
                )
                continue

            destination = self._unique_destination(packet_dir / "02_source_files", source_path.name)
            shutil.copy2(source_path, destination)
            manifest_rows.append(
                self._manifest_row(
                    source_path=source_path,
                    packet_path=destination,
                    packet_dir=packet_dir,
                    category="source_file",
                    role="Source transaction file referenced by imported data",
                    status="COPIED",
                )
            )

        self._write_methodology(packet_dir, transactions)
        self._write_tax_reports(packet_dir, transactions)
        self._write_tax_filing_alignment(packet_dir, transactions)
        self._write_holdings_reports(packet_dir, transactions)
        self._write_import_warnings(packet_dir, transactions)
        self._write_manifest(packet_dir, manifest_rows)
        self._write_inventory(packet_dir)
        self._write_summary(packet_dir, manifest_rows, transactions)

        return str(packet_dir)

    def _source_paths(self, transactions):
        sources = set()
        for transaction in transactions:
            source = getattr(transaction, "source", "")
            if source and os.path.exists(str(source)):
                sources.add(str(source))
        return sorted(sources)

    def _manifest_row(self, source_path, packet_path, packet_dir, category, role, status):
        source_path = Path(source_path)
        packet_path = Path(packet_path)
        return {
            "category": category,
            "role": role,
            "status": status,
            "source_path": str(source_path),
            "packet_relative_path": str(packet_path.relative_to(packet_dir)),
            "source_sha256": self._sha256(source_path),
            "packet_sha256": self._sha256(packet_path),
            "size_bytes": packet_path.stat().st_size,
            "last_write_time": datetime.fromtimestamp(packet_path.stat().st_mtime).isoformat(timespec="seconds"),
        }

    def _write_methodology(self, packet_dir, transactions):
        assets = ", ".join(sorted(transactions.assets)) if transactions.assets else "None"
        content = [
            "# Gainz Audit Packet",
            "",
            "This packet was generated locally by Gainz.",
            "",
            "Gainz links sale records to earlier buy lots according to the user's selected method. Unlinked sells, unexplained sends, and unexplained receives should be reviewed against source records before using generated reports.",
            "",
            f"Transaction count: {len(transactions.transactions)}",
            f"Assets: {assets}",
            "",
            "This packet is documentation support only. It is not legal, financial, or tax advice.",
        ]
        (packet_dir / "00_memos" / "METHODOLOGY.md").write_text("\n".join(content) + "\n", encoding="utf-8")

    def _write_manifest(self, packet_dir, rows):
        fieldnames = [
            "category",
            "role",
            "status",
            "source_path",
            "packet_relative_path",
            "source_sha256",
            "packet_sha256",
            "size_bytes",
            "last_write_time",
        ]
        with open(packet_dir / "03_manifests" / "evidence_manifest.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _write_tax_reports(self, packet_dir, transactions):
        all_rows = get_form_8949_report_rows(transactions)
        for term in ("short", "long"):
            self._write_form_8949_detail(
                packet_dir / "01_reports" / f"form_8949_{term}_term.csv",
                [row for row in all_rows if row["term"] == term],
            )

        totals = get_form_8949_totals(transactions)
        with open(packet_dir / "01_reports" / "form_8949_totals.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["term", "rows", "proceeds", "cost_basis", "gain_loss"],
            )
            writer.writeheader()
            for term in ("short", "long", "total"):
                row = totals[term]
                writer.writerow({
                    "term": term,
                    "rows": row["rows"],
                    "proceeds": f"{row['proceeds']:.2f}",
                    "cost_basis": f"{row['cost_basis']:.2f}",
                    "gain_loss": f"{row['gain_loss']:.2f}",
                })

        (packet_dir / "03_manifests" / "form_8949_totals.json").write_text(
            json.dumps(totals, indent=2),
            encoding="utf-8",
        )

    def _write_tax_filing_alignment(self, packet_dir, transactions):
        alignment = get_tax_filing_alignment_summary(transactions)
        fieldnames = [
            "year",
            "status",
            "calculated_rows",
            "calculated_proceeds",
            "reported_proceeds",
            "difference_proceeds",
            "calculated_cost_basis",
            "reported_cost_basis",
            "difference_cost_basis",
            "calculated_gain_loss",
            "reported_gain_loss",
            "difference_gain_loss",
            "tax_paid",
            "filing_status",
            "evidence_reference",
            "notes",
            "next_action",
        ]
        with open(packet_dir / "01_reports" / "tax_filing_alignment.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in alignment["rows"]:
                writer.writerow({
                    "year": row["year"],
                    "status": row["status"],
                    "calculated_rows": row["calculated_rows"],
                    "calculated_proceeds": f"{row['calculated_proceeds']:.2f}",
                    "reported_proceeds": self._format_optional_money(row["reported_proceeds"]),
                    "difference_proceeds": self._format_optional_money(row["difference_proceeds"]),
                    "calculated_cost_basis": f"{row['calculated_cost_basis']:.2f}",
                    "reported_cost_basis": self._format_optional_money(row["reported_cost_basis"]),
                    "difference_cost_basis": self._format_optional_money(row["difference_cost_basis"]),
                    "calculated_gain_loss": f"{row['calculated_gain_loss']:.2f}",
                    "reported_gain_loss": self._format_optional_money(row["reported_gain_loss"]),
                    "difference_gain_loss": self._format_optional_money(row["difference_gain_loss"]),
                    "tax_paid": self._format_optional_money(row["tax_paid"]),
                    "filing_status": row["filing_status"],
                    "evidence_reference": row["evidence_reference"],
                    "notes": row["notes"],
                    "next_action": row["next_action"],
                })

        (packet_dir / "03_manifests" / "tax_filing_alignment.json").write_text(
            json.dumps(alignment, indent=2),
            encoding="utf-8",
        )

    def _write_form_8949_detail(self, path, rows):
        fieldnames = FORM_8949_COLUMNS + ["link_id", "buy_uid", "sell_uid"]
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "description": row["description"],
                    "date_acquired": self._format_datetime(row["date_acquired"]),
                    "date_sold": self._format_datetime(row["date_sold"]),
                    "proceeds": f"{row['proceeds']:.2f}",
                    "cost_basis": f"{row['cost_basis']:.2f}",
                    "gain_loss": f"{row['gain_loss']:.2f}",
                    "source": row["source"],
                    "asset": row["asset"],
                    "quantity": format_quantity(row["quantity"]),
                    "term": row["term"],
                    "link_id": row["link_id"],
                    "buy_uid": row["buy_uid"],
                    "sell_uid": row["sell_uid"],
                })

    def _write_holdings_reports(self, packet_dir, transactions):
        reconciliation_rows = get_multi_asset_holdings_reconciliation_table_data(transactions)
        with open(packet_dir / "01_reports" / "holdings_reconciliation.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "asset",
                "declared_holdings",
                "expected_from_buys_sells_only",
                "imported_net_after_transfers",
                "available_lot_quantity",
                "difference_vs_declared",
                "status",
                "next_action",
            ])
            writer.writerows(reconciliation_rows)

        with open(packet_dir / "01_reports" / "current_holdings_lots.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "asset",
                    "type",
                    "acquired_at",
                    "estimated_held_quantity",
                    "original_quantity",
                    "usd_spot",
                    "estimated_basis",
                    "original_basis",
                    "source",
                ],
            )
            writer.writeheader()
            for asset in [row[0] for row in reconciliation_rows]:
                for lot in get_current_holdings_lots(transactions, asset):
                    writer.writerow({
                        "asset": lot["asset"],
                        "type": lot["type"],
                        "acquired_at": self._format_datetime(lot["acquired_at"]),
                        "estimated_held_quantity": format_quantity(lot["estimated_held_quantity"]),
                        "original_quantity": format_quantity(lot["original_quantity"]),
                        "usd_spot": f"{lot['usd_spot']:.2f}",
                        "estimated_basis": f"{lot['estimated_basis']:.2f}",
                        "original_basis": f"{lot['original_basis']:.2f}",
                        "source": lot["source"],
                    })

    def _write_import_warnings(self, packet_dir, transactions):
        warnings = getattr(transactions, "import_warnings", []) or []
        with open(packet_dir / "01_reports" / "import_warnings.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "source",
                    "row",
                    "date",
                    "type",
                    "asset",
                    "quantity",
                    "issue",
                    "likely_category",
                    "status",
                    "decision",
                    "note",
                    "next_action",
                    "warning",
                ],
            )
            writer.writeheader()
            for row in import_warning_review_rows(warnings, transactions=transactions):
                writer.writerow({
                    "source": row["source"],
                    "row": row["row"],
                    "date": row["row_date"],
                    "type": row["row_type"],
                    "asset": row["asset"],
                    "quantity": row["quantity"],
                    "issue": row["issue"],
                    "likely_category": row["likely_category"],
                    "status": row["review_status"],
                    "decision": row["decision_label"],
                    "note": row["review_note"],
                    "next_action": row["next_action"],
                    "warning": row["raw"],
                })

        with open(packet_dir / "01_reports" / "missing_basis_review.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["asset", "date", "quantity", "unlinked_quantity", "source", "status", "message", "note"],
            )
            writer.writeheader()
            writer.writerows(get_missing_basis_review_rows(transactions))

    def _write_inventory(self, packet_dir):
        rows = []
        for path in sorted(packet_dir.rglob("*")):
            if path.is_file():
                rows.append(
                    {
                        "packet_relative_path": str(path.relative_to(packet_dir)),
                        "sha256": self._sha256(path),
                        "size_bytes": path.stat().st_size,
                    }
                )

        with open(packet_dir / "03_manifests" / "packet_inventory.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["packet_relative_path", "sha256", "size_bytes"])
            writer.writeheader()
            writer.writerows(rows)

        with open(packet_dir / "03_manifests" / "SHA256SUMS.txt", "w", encoding="utf-8") as file:
            for row in rows:
                file.write(f"{row['sha256']}  {row['packet_relative_path'].replace(os.sep, '/')}\n")

    def _write_summary(self, packet_dir, manifest_rows, transactions):
        copied_sources = len([row for row in manifest_rows if row["status"] == "COPIED"])
        missing_sources = len([row for row in manifest_rows if row["status"] == "MISSING"])
        form_8949_totals = get_form_8949_totals(transactions)
        readiness = get_audit_readiness_summary(transactions)
        summary = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "packet_path": str(packet_dir),
            "copied_source_files": copied_sources,
            "missing_source_files": missing_sources,
            "manifest_entries": len(manifest_rows),
            "form_8949_totals": form_8949_totals,
            "tax_filing_alignment": get_tax_filing_alignment_summary(transactions),
            "holdings_reconciliation_rows": len(get_multi_asset_holdings_reconciliation_table_data(transactions)),
            "import_warning_count": len(getattr(transactions, "import_warnings", []) or []),
            "unresolved_import_warning_count": readiness["metrics"]["unresolved_import_warnings"],
            "missing_basis_rows": readiness["missing_records"]["basis"],
            "reconciliation_checklist": readiness["checklist"],
        }
        (packet_dir / "03_manifests" / "audit_packet_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

    def _unique_destination(self, directory, filename):
        candidate = directory / filename
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        index = 2
        while True:
            candidate = directory / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def _sha256(self, path):
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _format_datetime(self, value):
        if hasattr(value, "isoformat"):
            return value.isoformat(sep=" ", timespec="seconds")

        return value

    def _format_optional_money(self, value):
        if value is None:
            return ""

        return f"{value:.2f}"
