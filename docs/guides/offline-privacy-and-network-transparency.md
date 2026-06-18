---
title: Offline Privacy And Evidence Handling
description: Understand what Gainz stores locally, what it does not upload, and how reference-only evidence differs from copied evidence in audit packets.
---

# Offline Privacy And Evidence Handling

Gainz is designed for private offline crypto tax reconciliation. The normal workflow does not require a hosted account, exchange API sync, wallet sync, or transaction-history upload.

## What Gainz Stores Locally

Gainz stores working files on your computer:

- Imported transaction CSV copies.
- Saved revisions and workbook-style `.xlsx` saves.
- Generated Excel reports, CSV reports, JSON summaries, and Markdown notes.
- Audit packet folders.
- Tax evidence records, which are references by default.
- A local database for the app account and settings.

The local Gainz password gates the browser UI. It does not encrypt CSV, XLSX, JSON, Markdown, or audit packet files on disk. Protect the local data folder, export folders, backups, and synced folders the same way you protect other sensitive tax documents.

## What Gainz Does Not Require

Gainz does not require:

- Uploading transaction history to a hosted Gainz account.
- Connecting exchange API keys.
- Connecting wallets.
- Sending tax documents to a cloud parser.
- Storing your crypto history on a Gainz server.

External links such as the public website, GitHub Releases, docs, donation links, or update checks open only when you choose those actions outside the local reconciliation workflow.

## What Gainz Does Not Upload

Gainz does not upload imported transaction history, saved revisions, tax evidence files, generated workbooks, or audit packets to a Gainz-hosted service. Tax evidence scans record references by default. Evidence files are copied into audit packets only when you explicitly choose packet copy.

## Network Access That May Happen

The normal reconciliation workflow runs locally at `127.0.0.1`. Network access may happen when you intentionally open:

- The public website.
- GitHub Releases.
- Documentation or wiki links.
- Support or donation links.
- Any external resource opened from your browser outside the local Gainz workflow.

## OneDrive, iCloud, Dropbox, And Backups

Gainz stores files at the local paths shown in Privacy Mode. If those paths are inside OneDrive, iCloud, Dropbox, Google Drive, or another synced folder, that provider may sync the files according to your system settings. Use a non-synced folder for exports or audit packets you do not want synced by another service.

## How To Delete Local Data

1. Close Gainz so files are not in use.
2. Back up anything you need to keep.
3. Open Privacy Mode and note the local data, export, save, and audit packet folders.
4. Delete the local data folder, saved exports, and audit packet folders you no longer want.
5. Empty the recycle bin if you need those local copies removed from normal desktop recovery.

Deleting the local data folder removes app saves and account metadata for that Gainz install. It does not delete copies you already moved, uploaded, emailed, backed up, or synced through another service.

## Privacy Proof Checklist

Use this checklist to verify the private offline workflow:

- Gainz runs at `127.0.0.1`, which points back to your own computer.
- The app account is stored in the local database, not a hosted Gainz account.
- The core workflow uses CSV imports and manual review, not required exchange API keys or wallet connections.
- Tax evidence scans default to reference-only records.
- Audit packets include `PRIVACY_AND_EVIDENCE_HANDLING.md` and `FOR_CPAS.md`.
- The local password gates the browser UI but does not encrypt files on disk.
- Website, support, donation, and GitHub links open only when clicked.

## Reference-Only Evidence Vs Copied Evidence

Tax evidence scans default to reference-only handling.

Reference only means Gainz records the local file path or label in the tax evidence inventory and audit packet, but does not copy the file into the packet.

Copied means the file is included inside the audit packet and listed in `03_manifests/evidence_manifest.csv` with hashes.

Missing means Gainz had a saved local path for the evidence file, but the file was not present when the packet was generated.

## What Audit Packets Include

Audit packets include root-level status and handoff files:

- `README_FIRST.md`: human orientation, review order, folder map, and sharing reminder.
- `PACKET_STATUS.md`: detailed status, evidence counts, blockers, warnings, and work order review counts.
- `FOR_CPAS.md`: CPA-facing review order and evidence-handling orientation.
- `CPA_HANDOFF.md`: how the packet was generated and suggested review order.
- `PRIVACY_AND_EVIDENCE_HANDLING.md`: local storage and evidence-copy explanation.

Review these files before sharing a packet with a CPA or anyone else.

## Before Sharing A Packet

1. Open `03_manifests/evidence_manifest.csv`.
2. Check every copied source file and tax evidence file.
3. Confirm that reference-only paths are acceptable to share.
4. Remove files that should not be included.
5. Treat the packet like sensitive tax data.

Gainz is documentation support only. It is not legal, financial, accounting, filing, or tax advice.
