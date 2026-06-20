---
title: Current Crypto Holdings Reconciliation
description: Learn how Gainz compares declared holdings with imported buys, sells, sends, receives, available lots, and unlinked sales to find missing crypto records.
---

# Current Crypto Holdings Reconciliation

Current holdings reconciliation answers a plain question: does the activity you imported explain what you still hold today? If the answer is no, Gainz marks the asset for review so you can look for missing records before relying on tax reports.

![Gainz Holdings and Accounting walkthrough]({{ '/assets/screenshots/gainz-holdings-accounting.png' | relative_url }})
{: .screenshot-frame }

## Terms Gainz Uses

- **Declared holdings**: the amount you say you currently hold across exchanges, wallets, and custody accounts.
- **Calculated net from imported buys/sells**: buys minus sells from imported activity, before transfer-aware context.
- **Imported net after transfers**: imported buys and receives minus sells and sends.
- **Available lot quantity**: remaining acquisition lots available after sales and links are considered.
- **Difference**: declared holdings compared with calculated holdings.
- **Verified**: the imported activity and declared holdings agree within the app's tolerance.
- **Needs Review**: the imported activity and declared holdings do not line up yet.
- **Unlinked sales**: sells that exist but do not yet have complete basis links.
- **Needs user research**: a missing-basis item has been intentionally left unresolved with a note so source records can be investigated later.

## Why A Difference Happens

A difference can point to missing buys, missing sells, transfers between wallets, receives, sends, conversions, rewards, losses, unsupported CSV rows, or records from another platform. The number is not automatically wrong and it is not automatically taxable. It is a signal that the record set needs review.

Another cause is overlapping source files. For example, a full-history exchange export and a year-specific export may both include the same older activity. Gainz flags likely overlaps on **Import** and carries them into **Reports & Export** so you can remove duplicate or overlapping sources from the current data set after confirming the source files.

Sends are not automatically sales. A send to another account you own or control should remain a transfer. A send supported by records showing a sale, exchange, payment, fee, gift, or other transfer of ownership may need to be recorded as a taxable disposal. A possible lost, stolen, abandoned, or worthless lot should be marked for review and discussed with a qualified tax professional before relying on generated reports.

Receives are not automatically buys. A receive can be the other side of an owner transfer, a buy from another exchange, income, rewards, a gift, a transfer from a wallet that was not imported yet, or another acquisition that needs basis support.

If the user knows current holdings are zero for most assets, the bulk holdings step can set all non-primary tracked assets to zero and save one revision. This is useful for cases where a current portfolio statement shows only one remaining asset, but the imported history includes many older assets.

## Transfer Classification Review

**Reconcile** includes a **Transfer Classification Review** table for the selected asset. It lists send and receive rows separately from buys and sells because the CSV row type does not prove intent.

Use the table this way:

- If a send and receive have a nearby matching quantity, treat that as a clue for a possible owner transfer, then confirm with wallet/exchange records.
- If a send has no matching receive, find the destination. It may be an owner wallet that needs another source file, or it may be a documented taxable disposal, fee, gift, loss, or other ownership transfer.
- If a receive has no matching send, identify the source. It may be an owner transfer from an unimported wallet, a buy on another exchange, income, rewards, a gift, or another acquisition needing basis.
- Do not classify a row just to make the difference disappear. Add/import the missing source record when you have it; use optional classification tools only when documentation supports the treatment.
- If basis is still missing and source records are not available yet, mark the asset **Needs user research** with a note. Gainz keeps generated exports draft/not filing-ready while carrying the research status into Reports & Export and the audit packet.

## Review Workflow

1. Import every exchange and wallet file you can obtain.
2. Return to **Dashboard** and follow the highlighted current stage.
3. Open **Reconcile** and declare the amount you currently hold for each asset.
4. Click an asset marked **Needs Review** to inspect the selected asset workbench.
5. Review import warnings, unlinked sales, available lots, and the Transfer Classification Review table.
6. Add missing source files or supported manual entries when you have records for them.
7. Use optional classification tools only when documentation supports the treatment.
8. Mark missing-basis items as **Needs user research** only when they truly remain unresolved.
9. Run basis linking again when Dashboard or Reports & Export says sales still need basis.
10. Generate an audit packet only after unresolved items are understood and documented.

<div class="note-box">
  Gainz is documentation support. It helps you see where records agree or disagree, but it does not provide tax, legal, or financial advice.
</div>

## Related Guides

- [Synthetic crypto audit packet sample]({{ '/guides/sample-crypto-audit-packet/' | relative_url }})
- [What to give your CPA checklist]({{ '/guides/crypto-cpa-checklist/' | relative_url }})
- [How Gainz calculates basis]({{ '/how-gainz-calculates-basis/' | relative_url }})
- [Using Gainz from import to audit packet]({{ '/user-walkthrough/' | relative_url }})
