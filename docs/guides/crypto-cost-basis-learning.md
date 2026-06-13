---
title: Crypto Cost Basis Learning Path
description: Learn what crypto cost basis is, why missing basis happens, and how Gainz helps organize records for review without replacing professional tax advice.
---

# Crypto Cost Basis Learning Path

Cost basis is the record of what you paid to acquire crypto, including supported acquisition costs. When crypto is sold, exchanged, or otherwise disposed of, basis is compared with proceeds to calculate a gain or loss.

Gainz does not decide your filing position. It helps organize the records behind the question: **can every reported sale be explained by earlier acquisition records and current holdings?**

<div class="note-box">
This page is educational. It is not tax, legal, or financial advice. Review Gainz outputs with a qualified tax professional before filing.
</div>

## The Basic Idea

For a simple buy and sell:

```text
proceeds - cost basis = gain or loss
```

Crypto gets harder because a single asset can move through exchanges, wallets, conversions, rewards, transfers, gifts, and old accounts. A sale may be visible in one CSV while the original acquisition lives somewhere else.

## Learn The Concepts First

Good external learning resources help users understand why Gainz asks for complete CSVs, current holdings, and supporting notes.

- [Gordon Law Group's crypto cost basis guide](https://gordonlaw.com/learn/crypto-cost-basis/) is a plain-language overview of cost basis, proceeds, common methods, missing basis, and audit documentation issues.
- [IRS virtual currency transaction FAQs](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions) explain that virtual currency is treated as property, that gain or loss is based on adjusted basis versus amount received, and that records must support positions taken on returns.

## A Practical Workflow

<ol class="process-list">
  <li><strong>Collect every source file.</strong> Export CSVs from each exchange, app, wallet tool, and prior platform that touched the assets being reviewed.</li>
  <li><strong>Import and inspect warnings.</strong> Load files in Gainz and resolve skipped rows, unsupported conversions, or changed column names before relying on reports.</li>
  <li><strong>Link sells to earlier acquisitions.</strong> Use FIFO auto-link or a reviewed method to connect each sell quantity to a supported buy quantity.</li>
  <li><strong>Reconcile current holdings.</strong> Declare what is actually held today and compare it to what imported buys and sells imply should remain.</li>
  <li><strong>Explain the gaps.</strong> For differences, look for missing sales, sends, losses, transfers, gifts, income, rewards, or manually documented transactions.</li>
  <li><strong>Package evidence for review.</strong> Export the audit packet with source files, Form 8949-style rows, totals, import warnings, holdings reconciliation, and methodology notes.</li>
</ol>

## How Gainz Fits

Gainz is built for the middle of the workflow: turning raw transaction files into reviewable evidence.

<div class="grid">
  <div class="card">
    <h3>Basis Linking</h3>
    <p>Gainz links taxable sale quantities to earlier buy lots so cost basis can be inspected instead of guessed.</p>
  </div>
  <div class="card">
    <h3>Holdings Reconciliation</h3>
    <p>Gainz compares declared holdings with calculated holdings so missing activity becomes visible.</p>
  </div>
  <div class="card">
    <h3>Audit Packet</h3>
    <p>Gainz packages exports, warnings, source manifests, hashes, and methodology notes for review.</p>
  </div>
</div>

## Common Reasons Basis Is Missing

- The sale is imported, but the original buy was on another exchange.
- A transfer-in was really a prior acquisition that needs source records.
- A Coinbase Convert, swap, reward, gift, airdrop, staking deposit, or income event needs separate review.
- An old platform, wallet, or CSV export is missing.
- A row was skipped because a platform changed its column names.
- Current holdings do not match imported buys and sells, which means the transaction story is incomplete.

## What To Avoid

Do not enter numbers just to make warnings disappear. Manual transactions should be backed by source records, written notes, or professional review. A clean-looking report is only useful if the evidence behind it is explainable later.

## Next Steps In Gainz

- [Download Gainz]({{ '/download/' | relative_url }})
- [Use the walkthrough from import to audit packet]({{ '/user-walkthrough/' | relative_url }})
- [How Gainz calculates basis]({{ '/how-gainz-calculates-basis/' | relative_url }})
- [What to give your CPA]({{ '/guides/crypto-cpa-checklist/' | relative_url }})
