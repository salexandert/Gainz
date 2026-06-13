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

## Why A Difference Happens

A difference can point to missing buys, missing sells, transfers between wallets, receives, sends, conversions, rewards, losses, unsupported CSV rows, or records from another platform. The number is not automatically wrong and it is not automatically taxable. It is a signal that the record set needs review.

Sends are not automatically sales. A send to another account you own or control should remain a transfer. A send supported by records showing a sale, exchange, payment, fee, gift, or other transfer of ownership may need to be recorded as a taxable disposal. A possible lost, stolen, abandoned, or worthless lot should be marked for review and discussed with a qualified tax professional before relying on generated reports.

## Review Workflow

1. Import every exchange and wallet file you can obtain.
2. Open **Holdings & Accounting** and declare the amount you currently hold for each asset.
3. Click an asset marked **Needs Review** to inspect the selected asset workbench.
4. Review import warnings, unlinked sales, and available lots.
5. Add missing source files or supported manual entries when you have records for them.
6. Use optional classification tools only when documentation supports the treatment.
7. Run basis linking again, then refresh reconciliation.
8. Generate an audit packet only after unresolved items are understood and documented.

<div class="note-box">
  Gainz is documentation support. It helps you see where records agree or disagree, but it does not provide tax, legal, or financial advice.
</div>

## Related Guides

- [Synthetic crypto audit packet sample]({{ '/guides/sample-crypto-audit-packet/' | relative_url }})
- [What to give your CPA checklist]({{ '/guides/crypto-cpa-checklist/' | relative_url }})
- [How Gainz calculates basis]({{ '/how-gainz-calculates-basis/' | relative_url }})
- [Using Gainz from import to audit packet]({{ '/user-walkthrough/' | relative_url }})
