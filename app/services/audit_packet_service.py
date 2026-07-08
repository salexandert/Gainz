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
    unknown_gap_memos_markdown,
    unresolved_gap_memo_rows,
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

        report_path = ExportService(str(packet_dir / "01_reports")).export_to_excel(
            transactions,
            readiness=readiness,
        )
        if not readiness["is_ready"]:
            report_path = self._draft_report_path(report_path)
        report_dest = packet_dir / "01_reports" / Path(report_path).name
        if Path(report_path).resolve() != report_dest.resolve():
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
        self._write_reconciliation_work_order(packet_dir, readiness, transactions)
        self._write_unknown_gap_memos(packet_dir, readiness, transactions)
        self._write_packet_status_files(packet_dir, readiness, manifest_rows)
        self._write_cpa_handoff(packet_dir, readiness, manifest_rows, transactions)
        self._write_for_cpas(packet_dir, readiness, manifest_rows, transactions)
        self._write_privacy_and_evidence_handling(packet_dir, manifest_rows)
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

    def _draft_report_path(self, report_path):
        report_path = Path(report_path)
        if report_path.name.startswith("DRAFT_"):
            return str(report_path)

        candidate = report_path.with_name(f"DRAFT_{report_path.name}")
        if not candidate.exists():
            report_path.replace(candidate)
            return str(candidate)

        index = 2
        while True:
            candidate = report_path.with_name(f"DRAFT_{report_path.stem}_{index}{report_path.suffix}")
            if not candidate.exists():
                report_path.replace(candidate)
                return str(candidate)
            index += 1

    def _manifest_evidence_counts(self, manifest_rows):
        return {
            "copied_transaction_sources": len([
                row for row in manifest_rows
                if row["category"] == "source_file" and row["status"] == "COPIED"
            ]),
            "copied_tax_evidence": len([
                row for row in manifest_rows
                if row["category"] == "tax_evidence" and row["status"] == "COPIED"
            ]),
            "reference_only_evidence": len([
                row for row in manifest_rows
                if row["category"] == "tax_evidence" and row["status"] in ("REFERENCE", "REFERENCE_ONLY")
            ]),
            "missing_evidence": len([
                row for row in manifest_rows
                if row["category"] == "tax_evidence" and row["status"] == "MISSING"
            ]),
        }

    def _write_packet_status_files(self, packet_dir, readiness, manifest_rows):
        counts = self._manifest_evidence_counts(manifest_rows)
        status = "FILING-READY REVIEW PACKET" if readiness["is_ready"] else "DRAFT - NOT FILING READY"
        status_lines = [
            "# Gainz Packet Status",
            "",
            f"Status: {status}",
            f"Readiness: {readiness['status']}",
            f"Summary: {readiness['summary']}",
            f"Next action: {readiness['next_action']}",
            "",
            "## Evidence Handling",
            "",
            f"- Copied transaction source files: {counts['copied_transaction_sources']}",
            f"- Copied tax evidence files: {counts['copied_tax_evidence']}",
            f"- Reference-only tax evidence records: {counts['reference_only_evidence']}",
            f"- Missing tax evidence file paths: {counts['missing_evidence']}",
            "",
            "Reference only means the local file path or label is listed in the packet, but the file itself is not copied.",
            "Copied means the file is included inside `02_source_files/` and appears in the manifest with hashes.",
            "See `FOR_CPAS.md`, `CPA_HANDOFF.md`, and `PRIVACY_AND_EVIDENCE_HANDLING.md` before sharing this packet.",
            "",
            "## Open Blockers",
            "",
        ]
        status_lines.extend([f"- {blocker}" for blocker in readiness.get("blockers", [])] or ["- None"])
        status_lines.extend(["", "## Open Warnings", ""])
        status_lines.extend([f"- {warning}" for warning in readiness.get("warnings", [])] or ["- None"])
        work_order_summary = readiness.get("work_order_review_summary") or {}
        status_lines.extend([
            "",
            "## Work Order Review Decisions",
            "",
            f"- Work order items: {work_order_summary.get('total_items', 0)}",
            f"- Reviewed items: {work_order_summary.get('reviewed_count', 0)}",
            f"- Unreviewed items: {work_order_summary.get('unreviewed_count', 0)}",
            f"- Resolved: {work_order_summary.get('resolved_count', 0)}",
            f"- Import missing records: {work_order_summary.get('import_missing_records_count', 0)}",
            f"- Classify documented send as disposal: {work_order_summary.get('classify_documented_disposal_count', 0)}",
            f"- Keep as owner transfer: {work_order_summary.get('keep_owner_transfer_count', 0)}",
            f"- Document unknown basis: {work_order_summary.get('document_unknown_basis_count', 0)}",
            f"- Fork/airdrop acquisition: {work_order_summary.get('fork_airdrop_basis_count', 0)}",
            f"- Already included in filed tax totals: {work_order_summary.get('already_in_filed_totals_count', 0)}",
            f"- Treat unknown basis as $0 for CPA review: {work_order_summary.get('zero_basis_cpa_review_count', 0)}",
            f"- Needs research: {work_order_summary.get('needs_research_count', 0)}",
            f"- Leave unresolved for draft only: {work_order_summary.get('ignored_for_draft_count', 0)}",
            f"- Sent to CPA: {work_order_summary.get('sent_to_cpa_count', 0)}",
        ])
        status_lines.extend([
            "",
            "## Important",
            "",
            "Gainz is documentation support only. It is not legal, financial, accounting, filing, or tax advice.",
            "Review generated files and source records with a qualified tax professional before filing.",
            "",
        ])
        readme_lines = [
            "# Read This First",
            "",
            "This folder is a Gainz audit packet generated from local transaction records and review decisions.",
            "",
            f"Packet status: {status}",
            f"Readiness summary: {readiness['summary']}",
            "",
            "## Start Here",
            "",
            "1. Open `PACKET_STATUS.md` for the exact blocker, warning, and evidence counts.",
            "2. Open `FOR_CPAS.md` for the CPA-facing review order.",
            "3. Open `CPA_HANDOFF.md` for the generation notes.",
            "4. Open `PRIVACY_AND_EVIDENCE_HANDLING.md` before sharing the packet.",
            "5. Review `01_reports/reconciliation_work_order.csv` for the itemized work queue.",
            "6. Review `01_reports/unknown_gap_memos.md` for unresolved items that are documented for research or CPA review.",
            "",
            "## Folder Map",
            "",
            "- `01_reports/`: generated workbook, Form 8949-style CSVs, holdings reconciliation, tax evidence inventory, and work order outputs.",
            "- `02_source_files/`: copied transaction source files and explicitly copied tax evidence files.",
            "- `03_manifests/`: evidence manifest, packet inventory, hashes, and JSON summaries.",
            "- `00_memos/`: methodology and draft-status notes.",
            "",
            "## Evidence Handling",
            "",
            f"- Copied transaction source files: {counts['copied_transaction_sources']}",
            f"- Copied tax evidence files: {counts['copied_tax_evidence']}",
            f"- Reference-only tax evidence records: {counts['reference_only_evidence']}",
            f"- Missing tax evidence file paths: {counts['missing_evidence']}",
            "",
            "Reference-only evidence is listed for review but is not copied into this packet.",
            "",
            "Gainz is documentation support only. It is not legal, financial, accounting, filing, or tax advice.",
            "If sharing this packet with a tax professional, start with `FOR_CPAS.md`.",
            "",
        ]
        (packet_dir / "README_FIRST.md").write_text("\n".join(readme_lines), encoding="utf-8")
        (packet_dir / "PACKET_STATUS.md").write_text("\n".join(status_lines), encoding="utf-8")

    def _write_cpa_handoff(self, packet_dir, readiness, manifest_rows, transactions):
        counts = self._manifest_evidence_counts(manifest_rows)
        status = "FILING-READY REVIEW PACKET" if readiness["is_ready"] else "DRAFT - NOT FILING READY"
        assets = ", ".join(sorted(transactions.assets)) if transactions.assets else "None"
        lines = [
            "# CPA Handoff",
            "",
            f"Status: {status}",
            f"Readiness: {readiness['status']}",
            f"Summary: {readiness['summary']}",
            f"Next action: {readiness['next_action']}",
            "",
            "## How This Packet Was Generated",
            "",
            "- Gainz generated this packet locally from imported transaction records, user-entered holdings, review decisions, and tax evidence references stored on this computer.",
            "- The workbook in `01_reports/` was generated from the current Gainz save.",
            "- Transaction source files that still existed on disk were copied into `02_source_files/`.",
            "- Tax evidence is reference-only by default. Tax evidence files are copied only when the user explicitly marks them for packet copy.",
            "- Open blockers and warning decisions are preserved in `README_FIRST.md`, `PACKET_STATUS.md`, and the reconciliation work order files.",
            "",
            "## Packet Contents To Review",
            "",
            f"- Transactions: {len(transactions.transactions)}",
            f"- Assets: {assets}",
            f"- Copied transaction source files: {counts['copied_transaction_sources']}",
            f"- Copied tax evidence files: {counts['copied_tax_evidence']}",
            f"- Reference-only tax evidence records: {counts['reference_only_evidence']}",
            f"- Missing tax evidence file paths: {counts['missing_evidence']}",
            "",
            "## Suggested Review Order",
            "",
            "1. Open `README_FIRST.md` or `PACKET_STATUS.md` for readiness and open blockers.",
            "2. Review `01_reports/reconciliation_work_order.csv` for the itemized work queue.",
            "3. Review Form 8949-style detail and totals in the workbook and CSV reports.",
            "4. Review source files and evidence references before relying on generated totals.",
            "",
            "Gainz is documentation support only. It is not legal, financial, accounting, filing, or tax advice.",
            "",
        ]
        (packet_dir / "CPA_HANDOFF.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_for_cpas(self, packet_dir, readiness, manifest_rows, transactions):
        counts = self._manifest_evidence_counts(manifest_rows)
        status = "FILING-READY REVIEW PACKET" if readiness["is_ready"] else "DRAFT - NOT FILING READY"
        assets = ", ".join(sorted(transactions.assets)) if transactions.assets else "None"
        lines = [
            "# For CPAs",
            "",
            "This file is a concise orientation note for a tax professional reviewing a Gainz packet.",
            "Gainz is documentation support only. It does not provide legal, financial, accounting, filing, or tax advice.",
            "",
            "## Packet Status",
            "",
            f"- Status: {status}",
            f"- Readiness: {readiness['status']}",
            f"- Summary: {readiness['summary']}",
            f"- Next action: {readiness['next_action']}",
            f"- Transactions: {len(transactions.transactions)}",
            f"- Assets: {assets}",
            "",
            "## Suggested Review Order",
            "",
            "1. `PACKET_STATUS.md` for readiness, blockers, warnings, and evidence counts.",
            "2. `01_reports/reconciliation_work_order.csv` for the itemized unresolved work queue.",
            "3. `01_reports/unknown_gap_memos.md` for documented unknowns, user notes, candidate explanations, and CPA questions.",
            "4. `01_reports/tax_filing_alignment.csv` for calculated totals compared with user-entered filed totals.",
            "5. `01_reports/form_8949_totals.csv` and the Form 8949 detail CSVs for proceeds, basis, and gain/loss.",
            "6. `01_reports/holdings_reconciliation.csv` and `01_reports/current_holdings_lots.csv` for holdings explanation.",
            "7. `03_manifests/evidence_manifest.csv` for copied files, reference-only evidence, missing paths, and hashes.",
            "",
            "## Evidence Handling",
            "",
            f"- Copied transaction source files: {counts['copied_transaction_sources']}",
            f"- Copied tax evidence files: {counts['copied_tax_evidence']}",
            f"- Reference-only tax evidence records: {counts['reference_only_evidence']}",
            f"- Missing tax evidence file paths: {counts['missing_evidence']}",
            "",
            "Reference-only tax evidence records list a local path or label but do not include the file in this packet.",
            "Copied files are present in `02_source_files/` and are listed with hashes in the evidence manifest.",
            "",
            "## Items That Commonly Need Professional Judgment",
            "",
            "- Whether sends, receives, lost assets, transfers, conversions, and missing records were classified correctly.",
            "- Whether imported CSVs represent complete exchange, wallet, and brokerage history for the reviewed years.",
            "- Whether the user's filed totals and payment evidence align with generated Gainz totals.",
            "- Whether unresolved blockers make this packet draft-only.",
            "",
            "## Questions For The Taxpayer",
            "",
            "- Can you provide source records for missing acquisition-basis rows listed in `01_reports/reconciliation_work_order.csv`?",
            "- Do holdings discrepancies represent transfers, disposals, losses, gifts, unsupported rows, or missing imports?",
            "- Were filed totals based on another software package, exchange report, CPA adjustment, or manual calculation?",
            "- Which reference-only evidence files should be copied or shared for professional review?",
            "- Are any unresolved review decisions intentionally left for draft discussion rather than filing support?",
            "",
        ]
        (packet_dir / "FOR_CPAS.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_privacy_and_evidence_handling(self, packet_dir, manifest_rows):
        counts = self._manifest_evidence_counts(manifest_rows)
        lines = [
            "# Privacy And Evidence Handling",
            "",
            "Gainz is private offline crypto tax reconciliation software. This packet was generated locally on the user's computer.",
            "",
            "## Network And Storage Model",
            "",
            "- Gainz does not require a hosted account, exchange API sync, wallet sync, or transaction-history upload for this workflow.",
            "- Imported CSVs, saves, exports, audit packets, and evidence references are local files.",
            "- Local files remain on this computer unless the user shares, uploads, syncs, or backs them up through another service.",
            "- The local Gainz password gates the browser UI. It does not encrypt local CSV, XLSX, JSON, Markdown, or packet files.",
            "",
            "## Evidence Handling In This Packet",
            "",
            f"- Copied transaction source files: {counts['copied_transaction_sources']}",
            f"- Copied tax evidence files: {counts['copied_tax_evidence']}",
            f"- Reference-only tax evidence records: {counts['reference_only_evidence']}",
            f"- Missing tax evidence file paths: {counts['missing_evidence']}",
            "",
            "Reference only means the local file path or label is listed in the packet, but the file itself is not copied.",
            "Copied means the file is included inside `02_source_files/` and appears in `03_manifests/evidence_manifest.csv` with hashes.",
            "Missing means Gainz had a saved local path for the evidence file, but the file was not present when the packet was generated.",
            "",
            "## Before Sharing",
            "",
            "- Review `03_manifests/evidence_manifest.csv` for every copied or referenced file.",
            "- Remove any source files or evidence copies that should not be shared.",
            "- Treat this packet like sensitive tax data.",
            "",
        ]
        (packet_dir / "PRIVACY_AND_EVIDENCE_HANDLING.md").write_text("\n".join(lines), encoding="utf-8")

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
                    "status": "REFERENCE_ONLY",
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
            "combined_suggestions_count",
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
                    "combined_suggestions_count": row.get("combined_suggestions_count", 1),
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

    def _write_reconciliation_work_order(self, packet_dir, readiness, transactions):
        rows = reconciliation_work_order_rows(readiness, transactions)
        fieldnames = [
            "item_id",
            "priority",
            "priority_label",
            "blocker_type",
            "asset",
            "year",
            "date",
            "source_file",
            "suspected_issue",
            "next_action",
            "status",
            "review_decision",
            "review_decision_label",
            "review_note",
            "cpa_question",
            "review_updated_at",
            "what_gainz_knows",
            "what_gainz_does_not_know",
            "likely_explanations",
            "evidence_to_look_for",
            "plain_language_questions",
            "suggested_cpa_question",
        ]
        with open(packet_dir / "01_reports" / "reconciliation_work_order.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                csv_row = dict(row)
                for field in (
                    "what_gainz_knows",
                    "what_gainz_does_not_know",
                    "likely_explanations",
                    "evidence_to_look_for",
                    "plain_language_questions",
                ):
                    csv_row[field] = " | ".join(csv_row.get(field) or [])
                writer.writerow({field: csv_row.get(field, "") for field in fieldnames})

        (packet_dir / "01_reports" / "reconciliation_work_order.md").write_text(
            reconciliation_work_order_markdown(rows),
            encoding="utf-8",
        )

    def _write_unknown_gap_memos(self, packet_dir, readiness, transactions):
        rows = reconciliation_work_order_rows(readiness, transactions)
        memo_rows = unresolved_gap_memo_rows(rows)
        fieldnames = [
            "item_id",
            "blocker_type",
            "asset",
            "year",
            "date",
            "source_file",
            "amount_or_quantity_affected",
            "current_decision",
            "user_memory_notes",
            "cpa_question",
            "what_is_missing",
            "why_it_matters",
            "files_checked",
            "candidate_explanations",
            "evidence_to_look_for",
            "plain_language_questions",
            "next_action",
        ]
        with open(packet_dir / "01_reports" / "unknown_gap_memos.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(memo_rows)

        (packet_dir / "01_reports" / "unknown_gap_memos.md").write_text(
            unknown_gap_memos_markdown(rows),
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
            "work_order_review_summary": readiness.get("work_order_review_summary", {}),
            "reconciliation_work_order_rows": reconciliation_work_order_rows(readiness, transactions),
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
