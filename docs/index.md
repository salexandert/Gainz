---
title: Local Crypto Tax Audit Packet Tool
description: Gainz is local-first crypto tax software for reconciling exchange CSVs, linking cost basis, reviewing current holdings, and generating audit packets for CPA review.
schema_type: SoftwareApplication
---

<section class="hero">
  <div>
    <p class="eyebrow">Local-first crypto tax reconciliation</p>
    <h1>Gainz</h1>
    <p>Turn messy crypto exports into linked basis, Form 8949-style rows, current holdings reconciliation, and an audit packet you can review with a qualified tax professional.</p>
    <div class="button-row">
      <a class="button" href="{{ '/download/' | relative_url }}">Download Gainz for Windows</a>
      <a class="button-secondary" href="{{ '/user-walkthrough/' | relative_url }}">Start the walkthrough</a>
      <a class="button-secondary" href="{{ '/guides/crypto-form-8949-audit-packet/' | relative_url }}">See audit packet guide</a>
    </div>
  </div>
  <aside class="hero-visual" aria-label="Gainz trust summary">
    <img src="{{ '/assets/gainz_logo.png' | relative_url }}" alt="Gainz logo">
    <div class="metric-list">
      <div class="metric"><span>Runs</span><strong>Locally</strong></div>
      <div class="metric"><span>Imports</span><strong>Cash App, Coinbase, CSV</strong></div>
      <div class="metric"><span>Outputs</span><strong>Excel, 8949, audit packet</strong></div>
      <div class="metric"><span>Data</span><strong>Stays on your machine</strong></div>
    </div>
  </aside>
</section>

<section class="section-band">
  <h2>What Gainz Helps You Answer</h2>
  <div class="grid">
    <div class="card">
      <h3>What did I pay for this crypto?</h3>
      <p>Gainz links sale records to earlier buy lots so you can inspect the cost basis behind each Form 8949-style gain or loss.</p>
    </div>
    <div class="card">
      <h3>Do my current holdings make sense?</h3>
      <p>Reconciliation compares declared holdings, buys and sells, transfers, and current lot estimates across assets.</p>
    </div>
    <div class="card">
      <h3>Can I explain my tax work later?</h3>
      <p>Audit packets package Form 8949-style detail, totals, holdings reconciliation, import warnings, source manifests, and methodology notes.</p>
    </div>
  </div>
</section>

## Guides For Real Search Problems

These pages target the moments where people are stuck with exchange exports, missing basis, or audit documentation.

<ul class="guide-list">
  <li><a href="{{ '/guides/' | relative_url }}">Browse all crypto tax reconciliation guides</a></li>
  <li><a href="{{ '/guides/cash-app-bitcoin-tax-csv/' | relative_url }}">How to use a Cash App Bitcoin tax CSV in Gainz</a></li>
  <li><a href="{{ '/guides/coinbase-crypto-tax-csv/' | relative_url }}">How to import Coinbase crypto tax CSV files</a></li>
  <li><a href="{{ '/guides/coinbase-convert-crypto-tax/' | relative_url }}">How Gainz handles Coinbase Convert rows</a></li>
  <li><a href="{{ '/guides/coinbase-missing-cost-basis/' | relative_url }}">Troubleshoot missing Coinbase cost basis</a></li>
  <li><a href="{{ '/guides/current-holdings-reconciliation/' | relative_url }}">Understand current crypto holdings reconciliation</a></li>
  <li><a href="{{ '/guides/crypto-form-8949-audit-packet/' | relative_url }}">How to build a crypto Form 8949 audit packet</a></li>
  <li><a href="{{ '/guides/sample-crypto-audit-packet/' | relative_url }}">Download a synthetic crypto audit packet sample</a></li>
  <li><a href="{{ '/guides/crypto-cpa-checklist/' | relative_url }}">What to give your CPA for crypto CSV reconciliation</a></li>
  <li><a href="{{ '/guides/local-crypto-tax-software/' | relative_url }}">Why local crypto tax software matters for private tax data</a></li>
</ul>

## Download

The first public package is a local Windows build. It starts a desktop launcher window, runs Gainz on your own computer, and gives you a button to open the local web interface.

<p><a class="button" href="{{ '/download/' | relative_url }}">Go to the Download page</a></p>

## Public Website

The public Gainz website is <https://cryptogainz.store>. The temporary Netlify URL is <https://gainzstore.netlify.app/> while DNS and caches settle.

## Important Limit

Gainz is documentation support. It is not tax, legal, or financial advice. Always review exports with a qualified tax professional before filing.
