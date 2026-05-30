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

Status: in progress. Stats now includes declared HODL entry, current holdings reconciliation, and an estimated current-lot table after selecting an asset.

Current behavior:

- If no HODL is declared, Gainz shows available unlinked buy/receive lots.
- If HODL is declared, Gainz allocates that holding to newest available lots under a FIFO remaining estimate.
- The reconciliation summary compares declared HODL against buys minus sells and also shows imported net flow as a transfer diagnostic.

Open correctness work:

- Let users choose or document the lot allocation method more explicitly.
- Connect unresolved differences to suggested conversion/add-missing-transaction actions.

## Priority 3: Improve Import Confidence

- Coinbase `Convert` rows should keep importing as paired sell/buy legs with regression coverage.
- The Import page should show a summary of imported, duplicate, skipped, and warning rows immediately after upload.
- Demo CSVs should include edge cases: buys, sells, sends, receives, converts, fees, and fiat rows.

## Priority 4: Reduce UI Ambiguity

- Several pages rely on selecting a row before controls make sense; empty states should say what to select.
- Table labels should use consistent tax language: proceeds, cost basis, realized gain, remaining basis.
- Large tables need default sorting that matches workflow, usually oldest acquisition first for lots and disposal date for sales.

## Priority 5: Audit Packet Integration

- The audit packet should include a holdings-lot report, import warnings, selected save metadata, and reconciliation status.
- It should distinguish raw imported ledger evidence from tax-ready forms.

Status: in progress. Audit packets now include linked Form 8949 detail CSVs, Form 8949 totals, holdings reconciliation, current holdings lots, import warnings, the generated Excel report, copied source files, and packet manifests.

The Export page now shows an Audit Readiness panel before packet generation. It summarizes Form 8949 row count/totals, unlinked sales, HODL gaps, mismatches, warnings, next action, and packet contents.
