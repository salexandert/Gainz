---
title: Cash App Bitcoin Tax CSV Guide
description: Learn how Gainz imports Cash App Bitcoin CSV exports, links BTC sells to earlier buys, and packages evidence for tax review.
---

<article>

# Cash App Bitcoin Tax CSV Guide

Cash App can be a simple place to buy and sell Bitcoin, but tax time can still get uncomfortable when you need to support what you paid for each BTC sale. Gainz helps by importing Cash App CSV exports into a local ledger, then linking BTC sale records back to earlier buy lots.

## What To Export

Export your Cash App Bitcoin transaction history as CSV. Keep the original file unchanged and import a copy into Gainz.

Gainz expects the file name to identify the source. A name such as `cash_app_btc_2025.csv` or `cash_app_bitcoin_export.csv` helps the importer choose the Cash App parser.

## What Gainz Looks For

Gainz reads Bitcoin activity into transaction types:

- `buy`: BTC acquired with USD.
- `sell`: BTC disposed for USD.
- `send`: BTC moved out of the visible Cash App history.
- `receive`: BTC moved into the visible Cash App history.

Sells need basis links before generated reports are review-ready. Sends and receives are transfer evidence, not tax conclusions by themselves.

## Recommended Workflow

1. Start Gainz locally.
2. Open **Import**.
3. Upload the Cash App CSV.
4. Return to **Dashboard** and follow the highlighted current stage.
5. Declare current BTC holdings in **Reconcile**.
6. Review import warnings on **Import** and source gaps on **Reconcile**.
7. Let Gainz apply automatic FIFO basis links when matching BTC buys are available; use **Auto Link** only if you need to recalculate or compare another method.
8. Review readiness and generate draft output from **Reports & Export**.

## What To Review Before Filing

Pay special attention to unlinked BTC sells, sends that may represent disposals, receives that may need outside basis, and any holdings item marked Needs Review. Those are signs that the Cash App CSV alone may not tell the full story.

Gainz is local documentation support, not tax advice. Review the output with a qualified tax professional.

</article>
