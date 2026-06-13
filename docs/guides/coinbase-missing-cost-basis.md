---
title: Coinbase Missing Cost Basis Troubleshooting
description: Troubleshoot missing Coinbase crypto cost basis by checking import warnings, Convert rows, Coinbase Pro history, transfers, rewards, and manual wallet activity in Gainz.
---

# Coinbase Missing Cost Basis Troubleshooting

Missing Coinbase basis usually means the sale exists, but the earlier acquisition is incomplete, skipped, or classified in a way that needs review. Gainz helps surface that gap so you can collect the missing records instead of guessing.

![Gainz Import and Manage Data page]({{ '/assets/screenshots/gainz-import-manage-data.png' | relative_url }})
{: .screenshot-frame }

## Common Causes

- The Coinbase CSV does not cover the full account history.
- Older Coinbase Pro or GDAX fills are in a separate export.
- Convert rows were exported differently than buys and sells.
- Crypto was transferred in from another wallet or exchange before it was sold.
- Rewards, income, staking, gifts, or airdrops need supporting records.
- Sends, receives, swaps, or losses were skipped or imported with unsupported columns.
- Coinbase changed a column name and the importer needs column mapping.

## How To Troubleshoot In Gainz

1. Import all available Coinbase, Coinbase Pro, GDAX, and related exchange files.
2. Review **Import & Manage Data** for warnings, skipped rows, and data sources.
3. If automatic detection cannot find the needed fields, use the column mapper to select the header row and map date, type, asset, quantity, and USD value columns.
4. Confirm Coinbase Convert rows appear as both the disposed asset and the acquired asset.
5. Run FIFO auto-link for the affected asset, then check **Stats & Charts** for remaining unlinked sales.
6. Declare current holdings in **Holdings & Accounting** and review whether the calculated balance matches what you actually hold.
7. Add manual transactions only when you have source records that support the entry.

![Gainz Holdings and Accounting needs-review view]({{ '/assets/screenshots/gainz-holdings-accounting.png' | relative_url }})
{: .screenshot-frame }

## What Not To Do

Do not invent basis just to make a warning disappear. Do not ignore skipped rows. Do not treat a transfer as taxable or non-taxable without supporting facts. Gainz can organize the records and expose the gap, but a qualified tax professional should decide the filing treatment.

## Related Guides

- [Coinbase crypto tax CSV import guide]({{ '/guides/coinbase-crypto-tax-csv/' | relative_url }})
- [Coinbase Convert crypto tax guide]({{ '/guides/coinbase-convert-crypto-tax/' | relative_url }})
- [What to give your CPA checklist]({{ '/guides/crypto-cpa-checklist/' | relative_url }})
- [Current crypto holdings reconciliation]({{ '/guides/current-holdings-reconciliation/' | relative_url }})
