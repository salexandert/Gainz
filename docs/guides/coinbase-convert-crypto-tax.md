---
title: Coinbase Convert Crypto Tax Guide
description: Learn how Gainz treats Coinbase Convert rows as paired disposal and acquisition evidence for crypto tax reconciliation.
---

<article>

# Coinbase Convert Crypto Tax Guide

Coinbase Convert activity can be easy to misunderstand. Converting one crypto asset into another usually needs to be reviewed as a disposal of the asset you gave up and an acquisition of the asset you received.

Gainz imports supported Coinbase Convert rows as paired legs so the conversion does not disappear from the tax workflow.

## How Gainz Models Converts

A supported convert can create:

- A sell-like leg for the asset leaving your account.
- A buy-like leg for the asset entering your account.

That structure gives the outgoing asset a taxable disposition to link against earlier basis, while the incoming asset becomes a new lot for future basis review.

## Why Warnings Matter

Coinbase export formats can change. If Gainz cannot confidently interpret a convert row, it should surface an import warning. Do not ignore skipped or warned convert rows; they can change gains, losses, and current holdings.

## Review Checklist

1. Import the Coinbase file.
2. Check import warnings on **Stats & Charts**.
3. Confirm both sides of expected converts appear in the ledger.
4. Run auto-linking for assets with sells.
5. Reconcile current holdings across all converted assets.
6. Include import warnings and holdings reconciliation in the audit packet.

Gainz helps organize the evidence. It does not decide your tax treatment for you.

</article>
