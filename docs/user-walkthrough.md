# Using Gainz From Import To Audit Packet

This walkthrough shows the intended end-to-end Gainz workflow. Use the demo CSVs first if you are learning the product, then repeat the same process with your real exchange exports.

Gainz runs locally. Imported files, generated saves, exports, and audit packets stay on your computer unless you choose to share them.

If cost basis is new to you, start with the [crypto cost basis learning path]({{ '/guides/crypto-cost-basis-learning/' | relative_url }}), then return here for the click-by-click Gainz flow.

## 1. Start Gainz

From source:

```powershell
python launcher.py
```

The launcher opens a small desktop window with the local web address, usually:

```text
http://127.0.0.1:5000/
```

On first run, Gainz asks you to create a local admin account in the browser. The password is hashed into the local database and is not written to a plaintext credentials file.

If you forget the local password, use **Reset Password** in the launcher. The local password gates the browser UI; it does not encrypt imported CSVs, XLSX saves, exports, or audit packets. See [Reset Your Local Gainz Password]({{ '/guides/local-password-reset/' | relative_url }}).

![Gainz home page after opening the local app]({{ '/assets/screenshots/gainz-home.png' | relative_url }})
{: .screenshot-frame }

## 2. Import Transaction Files

Open **Import & Manage Data**.

If you are learning Gainz, click **Try Demo Data**. This loads the bundled synthetic Cash App, Coinbase, and Coinbase Convert files so you can reach Stats, Auto Link, and Export quickly.

Upload one file at a time. Gainz shows how many rows were imported, skipped, or warned after each upload.

Supported workflows currently include:

- Cash App CSV exports
- Coinbase CSV exports
- Coinbase Convert rows
- Coinbase Pro / GDAX fills
- Kraken/custom template imports
- Batch manual transaction entry

File names help Gainz detect the parser. Use names that include terms such as `cash_app`, `coinbase`, `coinbase_pro`, `gdax`, or `kraken`.

Gainz also recognizes common column-name variations. For example, headers like `Transaction Date`, `Activity Type`, `Crypto Quantity`, `Token Symbol`, `Spot Price USD`, and `Transaction Value` can be mapped into the import fields even when an exchange changes its export wording. If the columns are too unusual, Gainz will ask for the header row and let you choose the Date/time, Transaction type, Asset symbol, Asset quantity, and USD price/value columns.

If a CSV is missing known buys or sells, use **Add Manual Transactions** on the same page. Enter as many rows as needed, leave unused rows blank, and submit the batch. Gainz saves the batch as one revision with source `Gainz App Manual Add`.

![Gainz manual transaction batch entry table]({{ '/assets/screenshots/gainz-manual-batch-entry.png' | relative_url }})
{: .screenshot-frame }

For a safe test run, upload:

```text
demo_data/cash_app_sample.csv
demo_data/coinbase_sample.csv
demo_data/coinbase_convert_sample.csv
```

![Gainz Import and Manage Data page]({{ '/assets/screenshots/gainz-import-manage-data.png' | relative_url }})
{: .screenshot-frame }

## 3. Check Stats And Warnings

Open **Stats & Charts** after importing.

The top summary band answers the first important question: is the file set ready enough to trust?

Watch these values:

- `Reconciliation`: overall readiness.
- `Assets needing holdings`: assets where you have not entered current holdings.
- `Needs review`: declared holdings do not reconcile with imported buys/sells.
- `Import warnings`: rows Gainz could not fully interpret.
- `Unlinked sales`: sells that do not yet have basis links.

If sells exist and links are missing, Gainz will show `Not ready`. That is expected before auto-linking.

![Gainz Stats and Charts review page]({{ '/assets/screenshots/gainz-stats-charts.png' | relative_url }})
{: .screenshot-frame }

## 4. Link Sells To Earlier Buys

Open **Auto Link**.

Select an asset row, choose a year or `All Time`, then choose a linking method:

- `FIFO`: oldest available buys first.
- `FILO`: newest available buys first.
- `Min Gain`: higher-basis lots first for comparison under your selected method.
- `Min Gain Long`: long-term lots first for comparison under your selected method.

For a simple first review pass, use `FIFO`.

Repeat for every asset with unlinked sales. Then return to **Stats & Charts** and confirm `Unlinked sales` has dropped.

## 5. Declare Current Holdings

Open **Holdings & Accounting**.

This page is the guided current-holdings walkthrough. For each asset:

1. Select the asset row.
2. Enter the amount you currently hold across wallets and exchanges.
3. Save declared holdings.
4. Review the status and guidance.

Gainz compares:

- `Calculated Net From Imported Buys/Sells`: buys minus sells.
- `Imported Net Including Transfers`: buys plus receives minus sells minus sends.
- `Declared Holdings`: what you say you actually hold today.

If the status is `Needs Review`, review missing buys, missing disposals, sends, receives, gifts, income, losses, or conversions.

Use **Transfer Classification Review** for the selected asset. It shows send and receive rows as questions to answer:

- Did this send go to another wallet or exchange you own, or did it leave your ownership?
- Did this receive come from another account you own, or was it a buy, income, reward, gift, or other acquisition?
- Is there a nearby same-quantity send/receive pair that may be an owner transfer?
- What source record supports the classification?

Keep owner transfers as transfers. Record a documented disposal or basis-supported acquisition only when source records support it.

![Gainz Holdings and Accounting walkthrough]({{ '/assets/screenshots/gainz-holdings-accounting.png' | relative_url }})
{: .screenshot-frame }

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

## 7. Review Audit Packet Status

Open **Export**.

The **Audit Packet Review Status** panel summarizes whether the packet is ready for review:

- Form 8949 row count.
- Form 8949 gain/loss total.
- Unlinked sales count.
- Holdings gaps.
- Holdings review items.
- Import warnings.
- Review guidance.

If the status is `Not ready`, review the listed blockers before using the packet.

![Gainz Export audit readiness panel]({{ '/assets/screenshots/gainz-export-audit-readiness.png' | relative_url }})
{: .screenshot-frame }

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

Before filing, review outputs yourself and with a qualified tax professional. Pay special attention to import warnings, unlinked sales, holdings review items, manually reclassified transactions, and any asset whose source history is incomplete.
