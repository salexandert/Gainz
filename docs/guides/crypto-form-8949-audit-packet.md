---
title: Crypto Form 8949 Audit Packet Guide
description: Build a local crypto tax audit packet with linked Form 8949 rows, totals, holdings reconciliation, import warnings, source manifests, and hashes.
---

<article>

# Crypto Form 8949 Audit Packet Guide

Crypto tax work is easier to review when generated totals can be traced back to source files and lot links. Gainz generates a local audit packet so you can review the evidence behind Form 8949-style rows before filing.

## What The Packet Includes

A Gainz audit packet can include:

- Excel workbook export.
- Form 8949 short-term detail CSV.
- Form 8949 long-term detail CSV.
- Form 8949 totals CSV and JSON.
- Tax filing review CSV and JSON.
- Tax evidence inventory CSV and JSON.
- Suggested filed totals CSV and JSON.
- Holdings reconciliation CSV.
- Current holdings lots CSV.
- Import warnings CSV with active warnings and preserved review decisions for warnings that were later cleared by source updates.
- Missing basis review CSV.
- Source overlap review CSV.
- Tax evidence references by default, with evidence files copied only when the user explicitly marks them for packet copy.
- Source file manifest.
- SHA-256 hashes.
- Methodology memo.
- A draft memo when unresolved blockers or warnings remain.

## Why Links Come First

Form 8949-style output is generated from links between sale records and earlier buy lots. If a sell is not linked, Gainz marks the packet as not ready for review instead of quietly producing a weak answer.

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

## Who This Helps

The packet is designed for personal review, CPA review, and later audit explanation. It is not a promise that the tax treatment is correct. It is a way to make the work inspectable.

</article>
