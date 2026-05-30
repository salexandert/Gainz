# Using Gainz From Import To Audit Packet

This walkthrough shows the intended end-to-end Gainz workflow. Use the demo CSVs first if you are learning the product, then repeat the same process with your real exchange exports.

Gainz runs locally. Imported files, generated saves, exports, and audit packets stay on your computer unless you choose to share them.

## 1. Start Gainz

From source:

```powershell
python launcher.py
```

The launcher opens a small desktop window with the local web address, usually:

```text
http://127.0.0.1:5000/
```

On first run, Gainz creates a local admin account. If you did not set `GAINZ_ADMIN_PASSWORD`, the generated password is written to:

```text
instance/first_run_credentials.txt
```

## 2. Import Transaction Files

Open **Import Transactions**.

Upload one file at a time. Gainz shows how many rows were imported, skipped, or warned after each upload.

Supported workflows currently include:

- Cash App CSV exports
- Coinbase CSV exports
- Coinbase Convert rows
- Coinbase Pro / GDAX fills
- Kraken/custom template imports
- Manual transaction entry

File names help Gainz detect the parser. Use names that include terms such as `cash_app`, `coinbase`, `coinbase_pro`, `gdax`, or `kraken`.

For a safe test run, upload:

```text
demo_data/cash_app_sample.csv
demo_data/coinbase_sample.csv
demo_data/coinbase_convert_sample.csv
```

## 3. Check Stats And Warnings

Open **Stats & Charts** after importing.

The top summary band answers the first important question: is the file set ready enough to trust?

Watch these values:

- `Reconciliation`: overall readiness.
- `Assets needing HODL`: assets where you have not entered current holdings.
- `Assets with mismatches`: declared holdings do not match imported buys/sells.
- `Import warnings`: rows Gainz could not fully interpret.
- `Unlinked sales`: sells that do not yet have basis links.

If sells exist and links are missing, Gainz will show `Not ready`. That is expected before auto-linking.

## 4. Link Sells To Earlier Buys

Open **Auto Link**.

Select an asset row, choose a year or `All Time`, then choose a linking method:

- `FIFO`: oldest available buys first.
- `FILO`: newest available buys first.
- `Min Gain`: higher-basis lots first, where appropriate for your chosen method.
- `Min Gain Long`: prefer long-term lots where possible.

Most first-time demo runs should start with `FIFO`.

Repeat for every asset with unlinked sales. Then return to **Stats & Charts** and confirm `Unlinked sales` has dropped.

## 5. Declare Current HODL

Open **HODL & Accounting**.

This page is the guided current-holdings walkthrough. For each asset:

1. Select the asset row.
2. Enter the amount you currently hold across wallets and exchanges.
3. Save declared HODL.
4. Review the status and next action.

Gainz compares:

- `Expected From Buys/Sells Only`: buys minus sells.
- `Imported Net After Transfers`: buys plus receives minus sells minus sends.
- `Declared HODL`: what you say you actually hold today.

If the status is `Mismatch`, review missing buys, missing disposals, sends, receives, gifts, income, losses, or conversions.

## 6. Review Current Lots

Open **Stats & Charts** and select an asset.

Review:

- Current holdings reconciliation.
- Current holdings lots.
- Sales rows.
- Form 8949 short-term rows.
- Form 8949 long-term rows.
- Unrealized current-lot chart.

The current-lot estimate explains which remaining acquisition lots support current holdings. This is especially useful when you need to explain how today's balance relates to past buys and sells.

## 7. Review Audit Readiness

Open **Export**.

The **Audit Readiness** panel summarizes whether the packet is worth generating:

- Form 8949 row count.
- Form 8949 gain/loss total.
- Unlinked sales count.
- HODL gaps.
- Holdings mismatches.
- Import warnings.
- Next action.

If the status is `Not ready`, follow the listed blockers before relying on the packet.

## 8. Generate Outputs

On **Export**, you can create:

- Excel workbook export.
- Audit packet.

The audit packet includes:

- Excel workbook with transactions, stats, links, sales, and 8949 sheets.
- Form 8949 short-term and long-term detail CSVs.
- Form 8949 totals CSV and JSON.
- Holdings reconciliation CSV.
- Current holdings lots CSV.
- Import warnings CSV.
- Source files copied into the packet when they are still available on disk.
- Evidence manifest.
- Packet inventory.
- SHA-256 hashes.
- Methodology memo.

## 9. Review Before Filing

Gainz is documentation support. It is not tax, legal, or financial advice.

Before filing, review outputs yourself and with a qualified tax professional. Pay special attention to import warnings, unlinked sales, holdings mismatches, manually converted transactions, and any asset whose source history is incomplete.

## Current First-Run Improvements Planned

The first-user walkthrough surfaced a few high-value improvements:

- Add a **Load Demo Data** button so users can try Gainz without finding files manually.
- Add **Run FIFO Auto Link For All Assets** for a smoother first pass.
- Add **Use Expected HODL** actions for demo and clearly matched import sets.
- Link Export readiness blockers directly to the page/action that fixes each issue.
- Add a visible file-picker button next to drag-and-drop upload.
