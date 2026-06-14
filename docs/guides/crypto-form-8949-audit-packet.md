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
- Holdings reconciliation CSV.
- Current holdings lots CSV.
- Import warnings CSV with review decisions.
- Missing basis review CSV.
- Source overlap review CSV.
- Source file manifest.
- SHA-256 hashes.
- Methodology memo.

## Why Links Come First

Form 8949-style output is generated from links between sale records and earlier buy lots. If a sell is not linked, Gainz marks the packet as not ready for review instead of quietly producing a weak answer.

## Readiness Signals

Before generating a packet, check:

- Unlinked sales are zero or intentionally explained.
- Import warnings have been reviewed.
- Possible overlapping source files have been reviewed.
- Declared holdings are entered for relevant assets.
- Holdings items marked Needs Review are resolved or documented.
- Missing basis items marked Needs user research are understood as draft-only blockers.
- Filed totals and payment records have been entered where you want prior-year alignment.
- Source files are preserved when possible.

## Who This Helps

The packet is designed for personal review, CPA review, and later audit explanation. It is not a promise that the tax treatment is correct. It is a way to make the work inspectable.

</article>
