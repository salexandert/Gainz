# Using Gainz From Import To Audit Packet

This walkthrough shows the intended end-to-end Gainz workflow. Use the demo CSVs first if you are learning the product, then repeat the same process with your real exchange exports.

Gainz runs locally. Imported files, generated saves, exports, and audit packets stay on your computer unless you choose to share them.

If cost basis is new to you, start with the [crypto cost basis learning path]({{ '/guides/crypto-cost-basis-learning/' | relative_url }}), then return here for the click-by-click Gainz flow.

## 1. Start Gainz

Download the latest package from the [Gainz download page]({{ '/download/' | relative_url }}), then:

1. Unzip `Gainz-Windows.zip` and double-click `Gainz.exe` on Windows, or unzip `Gainz-macOS.zip` and open `Gainz.app` on macOS.
2. Keep the launcher window open while using Gainz.
3. Click **Open Gainz** in the launcher window.

The launcher opens a small desktop window with the local web address, usually:

```text
http://127.0.0.1:5000/
```

On first run, Gainz asks you to create a local admin account in the browser. The password is hashed into the local database and is not written to a plaintext credentials file.

If you forget the local password, use **Reset Password** in the launcher. The local password gates the browser UI; it does not encrypt imported CSVs, XLSX saves, exports, or audit packets. See [Reset Your Local Gainz Password]({{ '/guides/local-password-reset/' | relative_url }}).

## 2. Use Guided Reconciliation

After sign-in, start on **Dashboard**. This opens the **Guided Reconciliation** flow.

The first screen is split into four numbered stages:

- **1 Import**: load exchange CSVs, demo data, or source-backed manual rows.
- **2 Declare Holdings**: enter what you currently hold.
- **3 Reconcile**: review holdings gaps, missing basis, transfer questions, and research notes.
- **4 Review & Export**: review readiness and generate the workbook or audit packet.

Gainz opens the stage that needs your attention now. You can click a lower stage to review what already happened. Future stages open as previews only and point you back to the current task until earlier work is ready. **Next step** stays locked when Gainz still needs the current stage completed.

Each stage includes **Done when** criteria so you know what has to be true before moving on. The old dashboard counts and review groups are still available under **Show status details**, but they are collapsed by default so the first thing you see is the current step.

![Gainz Guided Reconciliation]({{ '/assets/screenshots/gainz-home.png' | relative_url }})
{: .screenshot-frame }

## 3. Import Transaction Files

From **Guided Reconciliation**, click **Open import**. Gainz opens **Step 1: Import Data**.

The Import page is intentionally staged:

- Primary actions: **Try Demo Data** and the CSV upload area.
- Secondary actions: **Column review options**, which stay collapsed unless Gainz cannot confidently map the file or you choose to review headers first.
- Tertiary review: **Add manual rows**, **Show current import status**, and **Review data sources and revisions** stay collapsed until needed.

If you are learning Gainz, click **Try Demo Data**. This loads the bundled synthetic Cash App, Coinbase, and Coinbase Convert files so you can reach Reconcile and Reports & Export without using private records.

Upload one file at a time. Gainz shows how many rows were imported, skipped, or warned after each upload.

After data is loaded, click **Continue to Declare Holdings** when you have imported the source files you want included in this review pass.

Supported workflows currently include:

- Cash App CSV exports
- Coinbase CSV exports
- Coinbase Convert rows
- Coinbase Pro / GDAX fills
- Kraken/custom template imports
- Batch manual transaction entry

File names help Gainz detect the parser. Use names that include terms such as `cash_app`, `coinbase`, `coinbase_pro`, `gdax`, or `kraken`.

Gainz also recognizes common column-name variations. For example, headers like `Transaction Date`, `Activity Type`, `Crypto Quantity`, `Token Symbol`, `Spot Price USD`, and `Transaction Value` can be mapped into the import fields even when an exchange changes its export wording. If the columns are too unusual, Gainz asks for the header row and lets you choose the Date/time, Transaction type, Asset symbol, Asset quantity, and USD price/value columns.

If Gainz reports import warnings, review the warning table before relying on generated reports. If Gainz flags **Possible overlapping source files**, open **Review data sources and revisions**. Gainz flags pairs that look like a full-history export plus a year-specific export, or files with overlapping transaction signatures. If one source duplicates another, remove only the duplicate or overlapping source from current data and keep the original CSV for evidence.

![Gainz Import page]({{ '/assets/screenshots/gainz-import-manage-data.png' | relative_url }})
{: .screenshot-frame }

## 4. Add Source-Backed Manual Rows When Needed

If a CSV is missing known buys or sells, open **Add manual rows** on the Import page.

Enter as many rows as needed, leave unused rows blank, and submit the batch. Gainz saves the batch as one revision with source `Gainz App Manual Add`.

![Gainz manual transaction batch entry table]({{ '/assets/screenshots/gainz-manual-batch-entry.png' | relative_url }})
{: .screenshot-frame }

For a safe test run, upload:

```text
demo_data/cash_app_sample.csv
demo_data/coinbase_sample.csv
demo_data/coinbase_convert_sample.csv
```

## 5. Follow Next Action And Declare Holdings

Return to **Dashboard** after importing and follow the highlighted current stage.

For most new imports, Gainz sends you to **Reconcile** first because current holdings tell Gainz whether imported buys and sells explain what you actually still hold.

On **Reconcile**:

1. Select an asset row.
2. Enter the amount you currently hold across wallets and exchanges.
3. Save declared holdings.
4. Review the status and guidance.

Gainz compares:

- `Calculated Net From Imported Buys/Sells`: buys minus sells.
- `Imported Net Including Transfers`: buys plus receives minus sells minus sends.
- `Declared Holdings`: what you say you actually hold today.

If the status is `Needs Review`, look for missing buys, missing disposals, sends, receives, gifts, income, losses, conversions, or overlapping source files.

If your records show you currently hold only a few assets, use **Bulk Current Holdings**. Enter one row for each asset you still hold, add another row when needed, then let Gainz set every other tracked asset to zero in one revision. Review the confirmation before continuing.

![Gainz Reconcile holdings walkthrough]({{ '/assets/screenshots/gainz-holdings-accounting.png' | relative_url }})
{: .screenshot-frame }

## 6. Review Import Warnings And Source Issues

Use **Import** for source warnings and source-management decisions.

If Gainz shows import warnings, review them before relying on generated reports. The warning table shows source file, row number, date, type, asset, quantity, issue, likely category, and review decision.

For each warning, choose whether it is:

- A true zero-value transfer.
- A row that needs a manual USD value.
- Something to ignore for now.
- Something that needs a note.

Unresolved warnings stay visible in Reports & Export and the audit packet.

## 7. Review Tax Evidence

Open **Tax Evidence** before generating a packet for a real filing review.

Use **Tax Evidence Inventory** to scan a local tax evidence folder or add one item at a time. Gainz classifies filenames and notes as filed returns, Form 8949, Schedule D, payment receipts, crypto workbooks, broker forms, transaction CSVs, estimates, or zero/not-applicable confirmations.

For broad folder scans, use the year, file type, include-keyword, and exclude-keyword filters. Scanned files are recorded as local references by default; Gainz does not copy them into audit packets unless you explicitly choose packet copy for a curated folder or evidence item.

Review **Confirm Suggested Filed Totals**. When Gainz can read clear values from local CSV, XLSX, or readable PDF evidence, it shows possible filed proceeds, cost basis, gain/loss, and tax-paid values with a confidence label and source file. Confirm, edit, or mark the year as needs research. Suggested totals are not treated as recorded filed totals until you save a review decision.

Use **Import Filed Totals from CSV** when you already have a year-by-year filed-total CSV. Gainz reports the actual number of rows imported and skipped. If a CSV only contains three years, Gainz imports three years and leaves the other evidence years visible for review.

## 8. Run FIFO And Basis Review When Dashboard Asks

Use **Auto Link** when Dashboard or Reports & Export says sales need basis links.

For a simple first review pass, use **FIFO**. FIFO links sales to the oldest available acquisition lots first, then creates Form 8949-style rows from those links.

Repeat for assets with unlinked sales. If a sale still needs earlier basis and you do not have the source records yet, return to **Reconcile**, choose **Leave Missing Basis As Needs Research**, and add a note. Gainz keeps exports draft/not filing-ready while showing that the missing basis is a known research item.

Use **Stats & Charts** as an advanced inspection page when you need deeper asset-level details, current-lot estimates, sales rows, Form 8949 rows, or charts. It is useful for analysis, but Dashboard and Reports & Export are the main workflow guides.

![Gainz Stats and Charts advanced review page]({{ '/assets/screenshots/gainz-stats-charts.png' | relative_url }})
{: .screenshot-frame }

## 9. Open Reports And Export

Open **Reports & Export** when Dashboard says you are ready to review output, or when you want to see exactly what is blocking readiness.

The **Readiness Review** panel shows:

- Reconciliation checklist.
- Form 8949 row count.
- Form 8949 gain/loss total.
- Unlinked sales count.
- Holdings gaps.
- Holdings review items.
- Import warnings and review decisions.
- Possible overlapping source files.
- Tax evidence inventory items.
- Missing acquisition basis before sales.
- Next action.

If the status is `Not ready`, review the listed blockers before using the packet. Gainz should tell you whether the blockers are current-holdings gaps, unreviewed import warnings, missing basis before sales, overlapping source files, missing tax evidence, or draft-only research items.

![Gainz Reports and Export readiness panel]({{ '/assets/screenshots/gainz-export-audit-readiness.png' | relative_url }})
{: .screenshot-frame }

## 10. Use The Guided Review Queue

If **Reports & Export** shows open work order items, click **Start guided review**.

The guided queue shows one unresolved item at a time:

- Issue.
- Why it matters.
- Recommended action.
- Asset, year, date, and source file when available.
- A link to the related page.
- Gap Investigator details: what Gainz knows, what Gainz does not know, likely explanations, evidence to look for, and plain-language questions.

Choose the review decision that matches what you found:

- `Resolved`
- `Import missing records`
- `Classify documented send as disposal`
- `Keep as owner transfer`
- `Document unknown basis`
- `Needs research`
- `Ignore for draft only`
- `Sent to CPA`

It is valid to choose an unresolved state when you do not know yet. Gainz keeps the item as a draft blocker and documents the uncertainty instead of forcing a guess.

Add user memory notes, files checked, and a CPA or future-research question when helpful. After saving, Gainz moves to the next open item. These decisions are saved into the reconciliation work order, dashboard readiness state, generated audit packet files, and the unknown gap memo outputs.

Use **Skip for now** when you need to keep moving without recording a decision yet. When every current work order item has a decision, Gainz shows an all-reviewed completion state and points you back to packet preview.

## 11. Expand Review Details Only When Needed

Reports & Export keeps raw evidence tables collapsed under **Review Details** so the page starts with the decision-making workflow.

Expand **Review Details** when you need row-level evidence for:

- Missing acquisition basis.
- Import warning decisions.
- Holdings explanations.
- Unknown gap memos.
- Source overlaps.
- Tax evidence inventory.
- Form 8949 totals.

Use those tables for review and documentation, not as the first place to decide what to do next.

## 12. Generate Outputs

On **Reports & Export**, choose an output folder and create:

- Excel workbook export.
- Audit packet.

Before generating an audit packet, review **Audit Packet Preview**. It shows:

- Copied files count.
- Reference-only tax evidence count.
- Missing evidence paths count.
- Draft or filing-ready status.
- Unresolved blockers and warnings.
- Output folder.
- Packet name pattern.

Reference only means the file path or label is listed, but the file is not copied. Copied means the file is included inside the audit packet and appears in the manifest with hashes.

If blockers remain, Gainz can generate draft output only after you acknowledge that unresolved review items remain. Draft output is marked in the filename and inside the generated workbook or packet status files.

After Gainz generates an audit packet, it opens a packet success screen with:

- Packet path.
- Draft or filing-ready status.
- Copied files count.
- Reference-only evidence count.
- Missing evidence paths count.
- Packet size and generated timestamp.
- Copy packet path.
- Copy CPA summary.
- Open packet folder.
- Open `README_FIRST.md`.
- The first files to review.

The audit packet includes:

- `README_FIRST.md`, `PACKET_STATUS.md`, `FOR_CPAS.md`, `CPA_HANDOFF.md`, and `PRIVACY_AND_EVIDENCE_HANDLING.md` at the packet root.
- Excel workbook with a visible `Packet Status` sheet plus transactions, stats, links, sales, and 8949 sheets.
- Form 8949 short-term and long-term detail CSVs.
- Form 8949 totals CSV and JSON.
- Tax filing review CSV and JSON.
- Tax evidence inventory CSV and JSON.
- Suggested filed totals CSV and JSON.
- Reconciliation work order CSV and Markdown.
- Unknown gap memo CSV and Markdown for unresolved items documented as research or CPA questions.
- Holdings reconciliation CSV.
- Current holdings lots CSV.
- Import warnings CSV with active warnings and preserved review decisions for warnings that were later cleared by source updates.
- Missing basis review CSV.
- Source overlap review CSV.
- Source files copied into the packet when they are still available on disk.
- Tax evidence references by default, plus tax evidence files copied only when explicitly marked for packet copy.
- Evidence manifest.
- Packet inventory.
- SHA-256 hashes.
- Methodology memo.
- `DRAFT_NOT_FILING_READY.md` when unresolved blockers or warnings remain.

## 13. Review Before Filing

Gainz is documentation support. It is not tax, legal, accounting, filing, or financial advice.

Before filing, review outputs yourself and with a qualified tax professional. Pay special attention to import warnings, unlinked sales, holdings review items, manually reclassified transactions, and any asset whose source history is incomplete.
