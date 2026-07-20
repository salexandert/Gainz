---
title: Crypto Form 8949 Audit Packet Guide
description: Build a local crypto tax audit packet with linked Form 8949 rows, totals, holdings reconciliation, import warnings, source manifests, and hashes.
---

<article>

# Crypto Form 8949 Audit Packet Guide

Crypto tax work is easier to review when generated totals can be traced back to source files and lot links. Gainz generates a local audit packet so you can review the evidence behind Form 8949-style rows before filing.

## What The Packet Includes

A Gainz audit packet can include:

- `README_FIRST.md`, `PACKET_STATUS.md`, `FOR_CPAS.md`, `CPA_HANDOFF.md`, and `PRIVACY_AND_EVIDENCE_HANDLING.md` at the packet root.
- Excel workbook export with a visible packet status sheet.
- Form 8949 short-term detail CSV when the input-integrity gate passes.
- Form 8949 long-term detail CSV when the input-integrity gate passes.
- Form 8949 totals CSV and JSON when the input-integrity gate passes.
- Tax filing review CSV and JSON.
- Tax evidence inventory CSV and JSON.
- Suggested filed totals CSV and JSON.
- Reconciliation work order CSV and Markdown.
- Unknown gap memo CSV and Markdown for unresolved items documented for research or CPA review.
- Holdings reconciliation CSV.
- Current holdings lots CSV.
- Import warnings CSV with active warnings and preserved review decisions for warnings that were later cleared by source updates.
- Missing basis review CSV.
- Source overlap review CSV.
- Tax evidence references by default, with evidence files copied only when the user explicitly marks them for packet copy.
- Source file manifest.
- SHA-256 hashes.
- Methodology memo.
- Draft markings in the packet name, workbook, and status files when unresolved blockers or warnings remain.

Before packet generation, the Reports & Export page shows an audit packet preview with copied file counts, reference-only counts, unresolved items, output folder, packet name, and draft status.

Reference only means the local path or label is listed, but the file is not copied. Copied means the file is included in the packet and listed in the manifest with hashes.

## Why Links Come First

Form 8949-style output is generated from links between sale records and earlier buy lots. If a sell is not linked, Gainz marks the packet as not ready for review instead of quietly producing a weak answer. If any source fails input-integrity checks, Gainz withholds Form 8949 and populated Gains/Sales sheets entirely and includes a `Calculations Suppressed` explanation instead.

## Readiness Signals

Before generating a packet, check:

- Unlinked sales are zero or intentionally explained.
- Active import warnings have been reviewed, and any cleared warning decisions remain visible in the packet.
- Possible overlapping source files have been reviewed.
- Tax evidence inventory says whether filed returns, crypto totals evidence, payment evidence, estimates, and zero/not-applicable confirmations are present by year.
- Suggested filed totals have been confirmed, edited, or marked as needs research.
- Declared holdings are entered for relevant assets.
- Holdings items marked Needs Review are resolved or documented.
- Missing basis items marked Needs user research are understood as draft-only blockers.
- Filed totals and payment records have been entered where you want prior-year alignment.
- Source files are preserved when possible.
- The packet preview shows only the files you expect to copy.

## Who This Helps

The packet is designed for personal review, CPA review, and later audit explanation. It is not a promise that the tax treatment is correct. It is a way to make the work inspectable.

</article>
