---
title: Coinbase Crypto Tax CSV Import Guide
description: Learn how Gainz imports Coinbase CSV files, flags warnings, creates reviewable basis links, and reconciles current crypto holdings locally.
---

<article>

# Coinbase Crypto Tax CSV Import Guide

Coinbase exports can include buys, sells, sends, receives, fees, and conversions. Gainz imports Coinbase CSV activity into a local crypto accounting workbench so you can inspect what happened before using generated reports.

## Before You Import

Download Coinbase transaction CSVs for the accounts and years you want to reconcile. Keep original exports unchanged. Import one file at a time so warnings are easier to understand.

File names should include `coinbase`, `coinbase_pro`, or `gdax` when appropriate. That helps Gainz select the right parser.

## After Import

Open **Stats & Charts** and check:

- Import warnings.
- Unlinked sales.
- Assets needing declared holdings.
- Assets marked Needs Review in holdings reconciliation.

An imported table is not automatically review-ready. Generated reports require basis links for sells and review of transfer gaps.

## Linking Coinbase Sells

Use **Auto Link** to connect Coinbase sells to earlier buy lots. FIFO is a common first review pass because it is easy to inspect, but Gainz also supports FILO and higher-basis comparison methods for review.

After linking, the Form 8949-style rows and audit packet totals are generated from those links.

## Current Holdings Reconciliation

Coinbase data may not include every wallet movement or external acquisition. Gainz compares declared holdings against imported buys, sells, sends, and receives so you can spot missing data before using the packet.

Gainz is not tax, legal, or financial advice. Use it to prepare documentation for review.

</article>
