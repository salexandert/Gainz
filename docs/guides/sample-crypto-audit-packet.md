---
title: Synthetic Crypto Audit Packet Sample
description: Download a synthetic Gainz audit packet sample and see how Form 8949 totals, holdings reconciliation, source manifests, hashes, and methodology notes fit together.
---

# Synthetic Crypto Audit Packet Sample

This sample packet uses synthetic demo data only. It is meant to show the shape of a review packet without exposing anyone's real exchange exports, wallet history, tax return, or private holdings.

<p><a class="button" href="https://cryptogainz.store/sample-packet/">View the public sample packet page</a></p>

<p><a class="button" href="{{ '/assets/downloads/gainz-synthetic-audit-packet-sample.zip' | relative_url }}">Download the synthetic sample packet</a></p>

The public sample page includes a visual folder tree so users and CPAs can see how the packet is organized before downloading the ZIP.

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
- `01_reports/form_8949_totals.csv`: short-term, long-term, and total proceeds, basis, and gain/loss totals.
- `01_reports/holdings_reconciliation.csv`: declared holdings compared with calculated holdings.
- `01_reports/import_warnings.csv`: a visible place for unsupported or skipped rows.
- `02_source_files/*.csv`: synthetic source CSVs for Cash App, Coinbase, and Coinbase Convert examples.
- `03_manifests/evidence_manifest.csv`: source file names, row counts, and SHA-256 hashes.
- `03_manifests/packet_inventory.csv`: a plain inventory of packet contents.

## Demo Totals

| Term | Rows | Proceeds | Cost Basis | Gain/Loss |
| --- | ---: | ---: | ---: | ---: |
| Short-term | 1 | $2,000.00 | $600.00 | $1,400.00 |
| Long-term | 2 | $5,700.00 | $3,800.00 | $1,900.00 |
| Total | 3 | $7,700.00 | $4,400.00 | $3,300.00 |

## What This Proves

- You can see the expected packet structure before trusting the workflow with real data.
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
