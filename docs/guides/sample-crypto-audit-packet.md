---
title: Synthetic Crypto Audit Packet Sample
description: Download a synthetic Gainz audit packet sample and see how Form 8949 totals, holdings reconciliation, source manifests, hashes, and methodology notes fit together.
---

# Synthetic Crypto Audit Packet Sample

This sample packet uses synthetic demo data only. It is meant to show the shape of a review packet without exposing anyone's real exchange exports, wallet history, tax return, or private holdings.

<p><a class="button" href="https://cryptogainz.store/sample-packet/">View the public sample packet page</a></p>

<p><a class="button" href="{{ '/assets/downloads/gainz-synthetic-audit-packet-sample.zip' | relative_url }}">Download the synthetic sample packet</a></p>

The public sample page includes a visual folder tree so users and CPAs can see how the packet is organized before downloading the ZIP. The sample is generated from Gainz itself, and machine-readable metadata records its exact version, generation date, checksum, scenario, and totals.

![Gainz Reports and Export readiness panel]({{ '/assets/screenshots/gainz-export-audit-readiness.png' | relative_url }})
{: .screenshot-frame }

## What Is Inside

The sample ZIP contains:

- `README_FIRST.md`: human orientation, review order, folder map, and sharing reminder.
- `PACKET_STATUS.md`: detailed status, evidence counts, blockers, warnings, and work order review counts.
- `FOR_CPAS.md`: CPA-facing review order, evidence-handling summary, and common professional judgment items.
- `CPA_HANDOFF.md`: how the packet was generated and suggested review order.
- `PRIVACY_AND_EVIDENCE_HANDLING.md`: reference-only vs copied evidence and local storage notes.
- `00_memos/METHODOLOGY.md`: a short explanation of how the synthetic records were prepared.
- `01_reports/reconciliation_work_order.csv`: a review queue of blockers, suspected issues, and next actions.
- `01_reports/unknown_gap_memos.md`: documented unknowns, user notes, candidate explanations, and CPA questions.
- `01_reports/import_economics.csv`: source gross values, fees, fee currencies, and total cost or net proceeds.
- `01_reports/cpa_resolution_workpapers.csv`: the exact unresolved sale quantity, user-recorded professional direction, evidence, assumption, before/after calculation receipt, and reversal identifiers.
- `01_reports/form_8949_totals.csv`: short-term, long-term, and total proceeds, basis, and gain/loss totals.
- `01_reports/holdings_reconciliation.csv`: declared holdings compared with calculated holdings.
- `01_reports/import_warnings.csv`: a visible place for unsupported or skipped rows.
- `02_source_files/coinbase_partial_basis_fee_sample.csv`: the synthetic fee-inclusive source rows used by this scenario.
- `03_manifests/evidence_manifest.csv`: source file names, row counts, and SHA-256 hashes.
- `03_manifests/packet_inventory.csv`: a plain inventory of packet contents.

## Demo Totals

| Term | Rows | Proceeds | Cost Basis | Gain/Loss |
| --- | ---: | ---: | ---: | ---: |
| Short-term | 1 | $297.00 | $0.00 | $297.00 |
| Long-term | 1 | $198.00 | $25.50 | $172.50 |
| Total | 2 | $495.00 | $25.50 | $469.50 |

The source reports `$5.50` of total USD fees: `$0.50` increases acquisition cost and `$5.00` reduces sale proceeds.

## What This Proves

- You can see the expected packet structure before trusting the workflow with real data.
- The documented 0.2 BCH FIFO lot is used first, including its acquisition fee.
- Only the exact unsupported 0.3 BCH remainder receives the recorded conservative treatment.
- The acquired date for that unsupported remainder stays blank and the workpaper identifies its short-term assumption.
- The before/after receipt moves Form 8949 totals from `$198.00` proceeds / `$25.50` basis / `$172.50` gain to `$495.00` proceeds / `$25.50` basis / `$469.50` gain.
- The professional-direction record is explicitly user-entered, unverified by Gainz, visible as a material assumption, and reversible.
- Totals are separated from source files, warnings, and methodology notes.
- The manifest creates a review trail for which source files were used.
- Reference-only evidence is listed without copying private files into the packet unless the user explicitly chooses packet copy.
- The CPA-facing orientation file gives a tax professional a short review order without hiding unresolved blockers.
- Holdings reconciliation sits beside tax-output totals instead of being a separate mental exercise.

## What Still Needs Professional Review

Gainz provides documentation support. It does not decide filing positions, taxable treatment, or whether a transaction should be reclassified. A qualified tax professional should review the source files, warnings, manual edits, basis method, holdings reconciliation, and final filing records before you rely on any output.

## Next Pages

- [Crypto Form 8949 audit packet guide]({{ '/guides/crypto-form-8949-audit-packet/' | relative_url }})
- [How Gainz calculates basis]({{ '/how-gainz-calculates-basis/' | relative_url }})
- [Using Gainz from import to audit packet]({{ '/user-walkthrough/' | relative_url }})
- [Download Gainz]({{ '/download/' | relative_url }})
