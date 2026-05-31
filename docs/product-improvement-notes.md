# Gainz Product Improvement Notes

These notes come from using Gainz locally with the demo files and the current private all-asset save.

## Priority 1: Make Reconciliation State Obvious

- Stats can display imported activity before tax basis links exist, so every tax-facing table should label unreconciled data clearly.
- Empty 8949 tables need a next action, not just a blank state.
- Import warnings should stay visible after reloads and saves.

Status: in progress. Stats now shows unreconciled warnings, import warnings, and next actions.

## Priority 2: Explain Current Holdings

- Users need to know what still appears held, when those lots were acquired, and the basis attached to each remaining lot.
- The most natural first version is a lot table driven by unlinked buy/receive quantities.
- Receives should stay visible because they may represent missing basis or externally acquired assets.
- Fiat movements should remain in the ledger but not appear as crypto assets.

Status: in progress. Stats now includes declared holdings entry, current holdings reconciliation, and an estimated current-lot table after selecting an asset.

Current behavior:

- If no holdings are declared, Gainz shows available unlinked buy/receive lots.
- If holdings are declared, Gainz allocates that holding to newest available lots under a FIFO remaining estimate.
- The reconciliation summary compares declared holdings against buys minus sells and also shows imported net flow as a transfer diagnostic.

Open correctness work:

- Let users choose or document the lot allocation method more explicitly.
- Connect unresolved differences to suggested conversion/add-missing-transaction actions.

## Priority 3: Improve Import Confidence

- Coinbase `Convert` rows should keep importing as paired sell/buy legs with regression coverage.
- The Import page should show a summary of imported, duplicate, skipped, and warning rows immediately after upload.
- CSV imports should tolerate common exchange header changes through a maintained alias dictionary.
- Demo CSVs should include edge cases: buys, sells, sends, receives, converts, fees, and fiat rows.

Status: in progress. The parser now uses a shared column-alias dictionary for Cash App, Coinbase, and generic CSV imports, detects header rows after short preambles, prompts for manual column mapping when required fields are unclear, and has regression tests for renamed headers plus golden demo Form 8949 totals.

## Priority 4: Reduce UI Ambiguity

- Several pages rely on selecting a row before controls make sense; empty states should say what to select.
- Table labels should use consistent tax language: proceeds, cost basis, realized gain, remaining basis.
- Large tables need default sorting that matches workflow, usually oldest acquisition first for lots and disposal date for sales.

First-user walkthrough notes:

- Import needed visible confirmation after each upload. Fixed with imported/skipped/warning counts.
- The drag-and-drop upload should eventually offer an explicit file-picker button and a "try demo data" path.
- Auto Link works, but the user has to know to select each asset and run a method. A guided "link all assets with FIFO" option would make demo and first-run use much easier.
- Holdings entry works, but users need a suggested value or "use expected holdings from current imports" action for test/demo data.
- Export readiness is helpful once the user reaches it. It should link directly back to the pages that resolve each blocker.

Recommended next first-run features:

1. Load Demo Data: one button that imports the bundled synthetic CSVs into a clean session. Status: shipped on Import & Manage Data.
2. Link All Assets: one guided action that runs FIFO for every asset with unlinked sells and reports failures.
3. Use Expected Holdings: when a user is using demo data or explicitly chooses to trust imported buys/sells, prefill declared holdings from expected quantity.
4. Readiness Blocker Links: each Export readiness blocker should point to Import, Auto Link, Holdings & Accounting, or Stats with the relevant asset selected.
5. Download/Open Output: after Export or Audit Packet generation, show the path inline and provide an obvious open-folder action in the desktop build.

These should be treated as adoption features, not just polish. They shorten the time from "I opened Gainz" to "I understand what this product does."

## Priority 5: Audit Packet Integration

- The audit packet should include a holdings-lot report, import warnings, selected save metadata, and reconciliation status.
- It should distinguish raw imported ledger evidence from tax-ready forms.

Status: in progress. Audit packets now include linked Form 8949 detail CSVs, Form 8949 totals, holdings reconciliation, current holdings lots, import warnings, the generated Excel report, copied source files, and packet manifests.

The Export page now shows an Audit Readiness panel before packet generation. It summarizes Form 8949 row count/totals, unlinked sales, holdings gaps, mismatches, warnings, next action, and packet contents.

## Discovery And Adoption Positioning

The strongest public positioning is:

> Gainz is a local-first crypto tax audit packet and reconciliation tool.

Discovery should target concrete, anxious searches rather than broad crypto-tax keywords:

- Coinbase cost basis missing.
- Cash App Bitcoin tax CSV.
- Crypto Form 8949 audit packet.
- Local crypto tax software.
- How to reconcile crypto CSVs.
- How to prove crypto tax basis.

Recommended public launch assets:

- GitHub Releases with a Windows build and checksums.
- A screenshot-driven demo using `demo_data/`.
- A sample audit packet generated only from synthetic data.
- A landing page focused on local-first privacy and CPA review packets.
- Import-specific guides for Cash App, Coinbase, Coinbase Convert, and Kraken/template workflows.
- A clear donation/support path for users who benefit from the free local tool.
