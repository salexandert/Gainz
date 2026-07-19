# Importer Coverage And Economic Fields

Gainz treats source economics as accounting data, not display-only metadata. Every imported buy or disposition should retain the source quantity, gross USD value, fee amount and currency, total cost or net proceeds, timestamp, source row, and source transaction ID when the file provides them.

The **Import > Confirm Imported Values** step shows what Gainz understood. The same rows are exported to `01_reports/import_economics.csv` in an audit packet and to the `Import Economics` workbook sheet.

## Coverage Matrix

| Source workflow | Detection | Quantity | Gross USD | Fee | Net tax value | Source trace | Important limits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cash App | Native | Yes | `Amount` | `Fee` and currency | `Net Amount`; buy fees increase total cost and sale fees reduce proceeds | Source row and transaction ID | Review zero-dollar withdrawals as transfer/classification questions. |
| Coinbase retail | Native | Yes | `Subtotal` | `Fees and/or Spread` and price currency | `Total (inclusive of fees and/or spread)` | Source row, ID, and notes | Source gross, fee, and total must reconcile within tolerance or output remains under review. |
| Coinbase official raw dual-leg export | Native with required preview | Both acquired and disposed quantities | Disposed-leg `Proceeds (excl. fees and/or spread) (USD)` | Included in the source-reported basis/proceeds fields when Coinbase does not provide a separate fee column | Acquired-leg `Cost Basis (incl. fees and/or spread) (USD)` and disposed-leg proceeds remain separate | Source row, transaction ID, notes, and acquired/disposed leg | Gainz shows source-row count, resulting legs, per-asset/type quantities, basis, proceeds, warnings, and skipped rows before commit. Fiat-only or unsupported rows remain unimported with a receipt. |
| Coinbase Convert | Native split into disposal and acquisition rows | Yes, both assets | Conversion subtotal | Preserved on the disposal side | Disposal net is preserved | Both rows retain the source row, ID, and note | When a fee exists, the acquired side remains an economic warning because Gainz will not silently choose how that fee affects acquired-asset basis. |
| Coinbase Pro / GDAX fills | Native | `size` | `total`, with price fallback | `fee` and `price/fee/total unit` | Buy fee increases cost; sale fee reduces proceeds | Source row and trade ID | A non-USD fee is preserved but blocks readiness until a supported USD value is supplied. |
| Kraken trade export | Advanced Import / Column Mapping | Map `vol` | Map `cost` | Map `fee` and quote currency | Derived from mapped gross and fee | Source row; map `txid` as transaction ID | Kraken is a tested mapping template, not a native auto-detected parser. Confirm the header and every mapped economic field. |
| Other CSVs | Advanced Import / Column Mapping | Required mapping | Map subtotal, gross value, or spot price | Optional fee and fee-currency mapping | Map net/total when available; otherwise Gainz derives it only when gross and a USD fee are supported | Source row and optional transaction ID/notes | If a fee is crypto-denominated or gross, fee, and net do not reconcile, Gainz preserves the source value and blocks readiness rather than guessing. |

## Sign And Fee Rules

- Gainz normalizes source signs by transaction type and stores asset quantity as a positive magnitude.
- A USD acquisition fee increases total cost.
- A USD disposition fee reduces net proceeds.
- Fees are included exactly once in Form 8949-style calculations.
- A crypto-denominated fee is retained with its source currency. Gainz does not invent a USD conversion; the row remains a review blocker.
- A derived value is labeled as calculated. Gainz does not describe a proportional allocation as directly source-reported.

## Input Integrity Gate

- Gainz reads CSV cells as source text before converting quantities or money. Small decimal quantities and scientific notation must resolve to the same value.
- When a source provides quantity, unit price, and total USD value, Gainz compares `quantity x price` with the source total using a documented tolerance.
- A material disagreement is an **input reliability blocker**, not an ordinary warning. Gainz suppresses Form 8949 and year-level calculated comparisons until the source is corrected or re-imported.
- Every imported, transformed, duplicate, unsupported, or skipped row receives a source-row receipt with file hash, row number, source transaction ID, interpreted quantity, outcome, and reason. The receipt is saved in revisions and exported as `01_reports/import_row_receipts.csv`.
- For Coinbase dual-leg rows, Gainz preserves the common source transaction ID and labels each resulting transaction as the acquired or disposed leg.

## Release-Gate Fixtures

Synthetic golden fixtures cover fee-inclusive round trips for Cash App, Coinbase, Coinbase Pro/GDAX, Coinbase Convert, generic mapped CSVs, and a Kraken mapped template. The partial-basis Coinbase fixture verifies this exact result:

```text
$495.00 net sale proceeds - $25.50 acquisition cost = $469.50 gain
```

The tests also verify the split between documented FIFO basis and an exact unsupported remainder, and confirm that an unresolved crypto-denominated fee prevents reconciliation-complete output.

## Before Relying On Output

1. Open **Import > Confirm Imported Values**.
2. Compare quantity, gross value, fee, fee currency, and total cost or net proceeds with the source row.
3. Resolve every economic warning or leave it documented as a draft blocker.
4. Review `import_economics.csv` with the source files and a qualified tax professional before filing.

Gainz provides reconciliation workpapers, not tax, legal, accounting, or filing advice.
