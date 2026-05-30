import csv
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from app.services.export_service import ExportService


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
        self._write_manifest(packet_dir, manifest_rows)
        self._write_inventory(packet_dir)
        self._write_summary(packet_dir, manifest_rows)

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
            "Gainz links taxable sells to earlier buy lots according to the user's selected accounting method. Unlinked sells, unexplained sends, and unexplained receives should be reviewed before relying on outputs.",
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

    def _write_summary(self, packet_dir, manifest_rows):
        copied_sources = len([row for row in manifest_rows if row["status"] == "COPIED"])
        missing_sources = len([row for row in manifest_rows if row["status"] == "MISSING"])
        summary = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "packet_path": str(packet_dir),
            "copied_source_files": copied_sources,
            "missing_source_files": missing_sources,
            "manifest_entries": len(manifest_rows),
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
