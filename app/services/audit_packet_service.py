import csv
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from app.services.export_service import ExportService
from app.services.import_warning_service import import_warning_audit_rows
from app.services.source_overlap_service import detect_source_overlaps
from app.services.tax_evidence_service import (
    get_tax_evidence_inventory_summary,
    tax_evidence_type_label,
)
from app.services.tax_total_extraction_service import get_suggested_filed_totals
from app.services.packet_plan_service import (
    reconciliation_work_order_markdown,
    reconciliation_work_order_rows,
    tax_evidence_packet_counts,
    transaction_source_paths,
)
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
        readiness = get_audit_readiness_summary(transactions)
        packet_prefix = "gainz_audit_packet" if readiness["is_ready"] else "gainz_audit_packet_DRAFT"
        packet_dir = self.packet_root / f"{packet_prefix}_{timestamp}"
        packet_dir.mkdir(parents=True, exist_ok=False)

        for folder in (
            "00_memos",
            "01_reports",
            "02_source_files",
            "03_manifests",
        ):
            (packet_dir / folder).mkdir(parents=True, exist_ok=True)

        manifest_rows = []

        report_path = ExportService(self.export_folder).export_to_excel(
            transactions,
            readiness=readiness,
        )
        report_dest = packet_dir / "01_reports" / Path(report_path).name
        if not readiness["is_ready"]:
            report_dest = packet_dir / "01_reports" / f"DRAFT_{Path(report_path).name}"
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

        manifest_rows.extend(self._copy_tax_evidence_files(packet_dir, transactions))

        if not readiness["is_ready"]:
            self._write_draft_not_ready_memo(packet_dir, readiness)
        self._write_methodology(packet_dir, transactions)
        self._write_tax_reports(packet_dir, transactions)
        self._write_tax_filing_alignment(packet_dir, transactions)
        self._write_tax_evidence_inventory(packet_dir, transactions)
        self._write_suggested_filed_totals(packet_dir, transactions)
        self._write_holdings_reports(packet_dir, transactions)
        self._write_import_warnings(packet_dir, transactions)
        self._write_source_overlap_review(packet_dir, transactions)
        self._write_reconciliation_work_order(packet_dir, readiness)
        self._write_packet_status_files(packet_dir, readiness, manifest_rows)
        self._write_manifest(packet_dir, manifest_rows)
        self._write_inventory(packet_dir)
        self._write_summary(packet_dir, manifest_rows, transactions)

        return str(packet_dir)

    def _write_draft_not_ready_memo(self, packet_dir, readiness):
        lines = [
            "# Draft Output: Not Filing Ready",
            "",
            "This audit packet was generated while Gainz still had unresolved review items.",
            "Use it for reconciliation review only. Do not treat it as filing-ready until blockers and warnings are resolved or documented.",
            "",
            f"Readiness status: {readiness['status']}",
            f"Summary: {readiness['summary']}",
            f"Next action: {readiness['next_action']}",
            "",
            "Open blockers:",
        ]
        blockers = readiness.get("blockers") or []
        lines.extend([f"- {blocker}" for blocker in blockers] or ["- None"])
        lines.extend(["", "Open warnings:"])
        warnings = readiness.get("warnings") or []
        lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
        lines.append("")

        (packet_dir / "00_memos" / "DRAFT_NOT_FILING_READY.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

    def _source_paths(self, transactions):
        return transaction_source_paths(transactions)

    def _write_packet_status_files(self, packet_dir, readiness, manifest_rows):
        copied_transaction_sources = len([
            row for row in manifest_rows
            if row["category"] == "source_file" and row["status"] == "COPIED"
        ])
        copied_tax_evidence = len([
            row for row in manifest_rows
            if row["category"] == "tax_evidence" and row["status"] == "COPIED"
        ])
        reference_only_evidence = len([
            row for row in manifest_rows
            if row["category"] == "tax_evidence" and row["status"] in ("REFERENCE", "REFERENCE_ONLY")
        ])
        missing_evidence = len([
            row for row in manifest_rows
            if row["category"] == "tax_evidence" and row["status"] == "MISSING"
        ])
        status = "FILING-READY REVIEW PACKET" if readiness["is_ready"] else "DRAFT - NOT FILING READY"
        lines = [
            "# Gainz Packet Status",
            "",
            f"Status: {status}",
            f"Readiness: {readiness['status']}",
            f"Summary: {readiness['summary']}",
            f"Next action: {readiness['next_action']}",
            "",
            "## Evidence Handling",
            "",
            f"- Copied transaction source files: {copied_transaction_sources}",
            f"- Copied tax evidence files: {copied_tax_evidence}",
            f"- Reference-only tax evidence records: {reference_only_evidence}",
            f"- Missing tax evidence file paths: {missing_evidence}",
            "",
            "Reference only means the local file path or label is listed in the packet, but the file itself is not copied.",
            "Copied means the file is included inside `02_source_files/` and appears in the manifest with hashes.",
            "",
            "## Open Blockers",
            "",
        ]
        lines.extend([f"- {blocker}" for blocker in readiness.get("blockers", [])] or ["- None"])
        lines.extend(["", "## Open Warnings", ""])
        lines.extend([f"- {warning}" for warning in readiness.get("warnings", [])] or ["- None"])
        lines.extend([
            "",
            "## Important",
            "",
            "Gainz is documentation support only. It is not legal, financial, accounting, filing, or tax advice.",
            "Review generated files and source records with a qualified tax professional before filing.",
            "",
        ])
        content = "\n".join(lines)
        (packet_dir / "README_FIRST.md").write_text(content, encoding="utf-8")
        (packet_dir / "PACKET_STATUS.md").write_text(content, encoding="utf-8")

    def _copy_tax_evidence_files(self, packet_dir, transactions):
        rows = []
        evidence_dir = packet_dir / "02_source_files" / "tax_evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        for record in getattr(transactions, "tax_evidence_records", []) or []:
            evidence_path = str(record.get("evidence_path") or "")
            evidence_type = tax_evidence_type_label(record.get("evidence_type"))
            role = f"Tax evidence for {record.get('year') or 'unassigned year'}: {evidence_type}"

            if not evidence_path:
                rows.append({
                    "category": "tax_evidence",
                    "role": role,
                    "status": "REFERENCE",
                    "source_path": record.get("evidence_label", ""),
                    "packet_relative_path": "",
                    "source_sha256": "",
                    "packet_sha256": "",
                    "size_bytes": "",
                    "last_write_time": "",
                })
                continue

            source_path = Path(evidence_path)
            if not source_path.exists() or not source_path.is_file():
                rows.append({
                    "category": "tax_evidence",
                    "role": role,
                    "status": "MISSING",
                    "source_path": str(source_path),
                    "packet_relative_path": "",
                    "source_sha256": "",
                    "packet_sha256": "",
                    "size_bytes": "",
                    "last_write_time": "",
                })
                continue

            if not record.get("copy_to_packet"):
                rows.append({
                    "category": "tax_evidence",
                    "role": role,
                    "status": "REFERENCE_ONLY",
                    "source_path": str(source_path),
                    "packet_relative_path": "",
                    "source_sha256": "",
                    "packet_sha256": "",
                    "size_bytes": "",
                    "last_write_time": "",
                })
                continue

            destination = self._unique_destination(evidence_dir, source_path.name)
            shutil.copy2(source_path, destination)
            rows.append(
                self._manifest_row(
                    source_path=source_path,
                    packet_path=destination,
                    packet_dir=packet_dir,
                    category="tax_evidence",
                    role=role,
                    status="COPIED",
                )
            )

        return rows

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

    def _write_tax_evidence_inventory(self, packet_dir, transactions):
        alignment = get_tax_filing_alignment_summary(transactions)
        inventory = get_tax_evidence_inventory_summary(transactions, alignment)
        with open(packet_dir / "01_reports" / "tax_evidence_inventory.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "year",
                    "calculated_totals",
                    "filed_return_evidence",
                    "payment_evidence",
                    "crypto_total_evidence",
                    "status",
                    "what_gainz_found",
                    "what_gainz_needs",
                    "next_action",
                ],
            )
            writer.writeheader()
            for row in inventory["rows"]:
                writer.writerow({
                    "year": row["year"],
                    "calculated_totals": row["calculated_totals"],
                    "filed_return_evidence": row["filed_return_evidence"],
                    "payment_evidence": row["payment_evidence"],
                    "crypto_total_evidence": row["crypto_total_evidence"],
                    "status": row["status"],
                    "what_gainz_found": row["what_gainz_found"],
                    "what_gainz_needs": row["what_gainz_needs"],
                    "next_action": row["next_action"],
                })

        with open(packet_dir / "01_reports" / "tax_evidence_items.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "year",
                    "evidence_type",
                    "evidence_label",
                    "evidence_path",
                    "packet_handling",
                    "notes",
                    "updated_at",
                ],
            )
            writer.writeheader()
            for record in inventory["evidence_records"]:
                writer.writerow({
                    "year": record.get("year") or "",
                    "evidence_type": record["evidence_type_label"],
                    "evidence_label": record.get("evidence_label", ""),
                    "evidence_path": record.get("evidence_path", ""),
                    "packet_handling": (
                        "Copy into packet"
                        if record.get("copy_to_packet")
                        else "Reference only"
                    ),
                    "notes": record.get("notes", ""),
                    "updated_at": record.get("updated_at", ""),
                })

        (packet_dir / "03_manifests" / "tax_evidence_inventory.json").write_text(
            json.dumps(inventory, indent=2),
            encoding="utf-8",
        )

    def _write_suggested_filed_totals(self, packet_dir, transactions):
        suggested_totals = get_suggested_filed_totals(transactions)
        fieldnames = [
            "year",
            "source_label",
            "evidence_type",
            "confidence",
            "reported_proceeds",
            "reported_cost_basis",
            "reported_gain_loss",
            "tax_paid",
            "matched_fields",
            "notes",
        ]
        with open(packet_dir / "01_reports" / "suggested_filed_totals.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in suggested_totals:
                writer.writerow({
                    "year": row.get("year") or "",
                    "source_label": row.get("source_label", ""),
                    "evidence_type": row.get("evidence_type_label", ""),
                    "confidence": row.get("confidence", ""),
                    "reported_proceeds": self._format_optional_money(row.get("reported_proceeds")),
                    "reported_cost_basis": self._format_optional_money(row.get("reported_cost_basis")),
                    "reported_gain_loss": self._format_optional_money(row.get("reported_gain_loss")),
                    "tax_paid": self._format_optional_money(row.get("tax_paid")),
                    "matched_fields": ", ".join(row.get("matched_fields", [])),
                    "notes": row.get("notes", ""),
                })

        (packet_dir / "03_manifests" / "suggested_filed_totals.json").write_text(
            json.dumps(suggested_totals, indent=2),
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
        with open(packet_dir / "01_reports" / "import_warnings.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "source",
                    "row",
                    "active_status",
                    "date",
                    "type",
                    "asset",
                    "quantity",
                    "issue",
                    "likely_category",
                    "status",
                    "decision",
                    "note",
                    "review_updated_at",
                    "next_action",
                    "warning",
                ],
            )
            writer.writeheader()
            for row in import_warning_audit_rows(transactions):
                writer.writerow({
                    "source": row["source"],
                    "row": row["row"],
                    "active_status": row["active_status"],
                    "date": row["row_date"],
                    "type": row["row_type"],
                    "asset": row["asset"],
                    "quantity": row["quantity"],
                    "issue": row["issue"],
                    "likely_category": row["likely_category"],
                    "status": row["review_status"],
                    "decision": row["decision_label"],
                    "note": row["review_note"],
                    "review_updated_at": row["review_updated_at"],
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

    def _write_source_overlap_review(self, packet_dir, transactions):
        with open(packet_dir / "01_reports" / "source_overlap_review.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "source_a",
                    "source_b",
                    "count_a",
                    "count_b",
                    "date_range_a",
                    "date_range_b",
                    "matching_rows",
                    "overlap_percent",
                    "status",
                    "message",
                    "next_action",
                ],
            )
            writer.writeheader()
            for row in detect_source_overlaps(transactions):
                writer.writerow({
                    "source_a": row["source_a"],
                    "source_b": row["source_b"],
                    "count_a": row["count_a"],
                    "count_b": row["count_b"],
                    "date_range_a": row["date_range_a"],
                    "date_range_b": row["date_range_b"],
                    "matching_rows": row["matching_rows"],
                    "overlap_percent": row["overlap_percent"],
                    "status": row["status"],
                    "message": row["message"],
                    "next_action": row["next_action"],
                })

    def _write_reconciliation_work_order(self, packet_dir, readiness):
        rows = reconciliation_work_order_rows(readiness)
        fieldnames = [
            "blocker_type",
            "asset",
            "year",
            "date",
            "source_file",
            "suspected_issue",
            "next_action",
            "status",
        ]
        with open(packet_dir / "01_reports" / "reconciliation_work_order.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        (packet_dir / "01_reports" / "reconciliation_work_order.md").write_text(
            reconciliation_work_order_markdown(rows),
            encoding="utf-8",
        )

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
        evidence_counts = tax_evidence_packet_counts(transactions)
        summary = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "packet_path": str(packet_dir),
            "copied_source_files": copied_sources,
            "missing_source_files": missing_sources,
            "tax_evidence_packet_counts": evidence_counts,
            "manifest_entries": len(manifest_rows),
            "form_8949_totals": form_8949_totals,
            "tax_filing_alignment": get_tax_filing_alignment_summary(transactions),
            "tax_evidence_inventory": get_tax_evidence_inventory_summary(transactions),
            "suggested_filed_totals": get_suggested_filed_totals(transactions),
            "readiness_status": readiness["status"],
            "readiness_is_ready": readiness["is_ready"],
            "readiness_summary": readiness["summary"],
            "readiness_blocker_groups": readiness["blocker_groups"],
            "holdings_reconciliation_rows": len(get_multi_asset_holdings_reconciliation_table_data(transactions)),
            "import_warning_count": len(getattr(transactions, "import_warnings", []) or []),
            "import_warning_review_count": len(getattr(transactions, "import_warning_reviews", []) or []),
            "unresolved_import_warning_count": readiness["metrics"]["unresolved_import_warnings"],
            "missing_basis_rows": readiness["missing_records"]["basis"],
            "source_overlap_rows": readiness["missing_records"]["source_overlaps"],
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
