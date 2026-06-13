# How Gainz Calculates Basis

Gainz models imported crypto activity as four transaction types:

- `buy`: creates cost basis.
- `sell`: creates a taxable disposition that needs basis.
- `send`: moves crypto out of the visible account history.
- `receive`: moves crypto into the visible account history.

The core accounting task is linking sell quantities to earlier buy quantities. Each link carries a proportional cost basis from the buy lot to the sell.

## Universal Wallet Model

Gainz uses a universal wallet model. It does not require every blockchain transfer to be present before it can estimate gains. Instead, it treats all imported transactions for the same asset as one pool, then asks whether the taxable sell events can be supported by earlier buys.

This is useful when exchange CSVs are incomplete or wallet transfers are hard to reconstruct. The tradeoff is that unexplained sends, receives, lost coins, gifts, or conversions still need user review.

## Linking Methods

Gainz supports several lot-selection strategies:

- FIFO: links the earliest available buy lots first.
- FILO: links the latest available buy lots first.
- Min Gain: links higher-cost lots first to reduce gain where allowed by the user's chosen method.
- Min Gain Long: favors long-term lots when applicable.

The selected method determines which buy lot supplies cost basis for each sell.

## Proceeds, Basis, and Gain

For each link:

```text
linked proceeds = linked quantity * sell spot price
linked basis    = linked quantity * buy spot price
gain/loss       = linked proceeds - linked basis
```

Form 8949 rows are generated from those links. For partial links, Gainz prorates buy-side fees into cost basis and sell-side fees against proceeds using the linked quantity divided by the source transaction quantity.

If a sell cannot be fully linked to earlier basis, Gainz reports the unlinked quantity. Unlinked sells are a warning condition, not a final answer.

## Short-Term vs Long-Term

Gainz compares the buy timestamp to the sell timestamp for each link:

- Short-term: held for one year or less.
- Long-term: held for more than one year.

Excel exports split Form 8949-style output by year and holding period.

## Sends and Receives

Sends and receives are not automatically taxable in Gainz. They are evidence that assets moved in or out of the visible transaction set.

If a receive is really an acquisition, it may need to be converted to a buy with basis. If a send is really a disposal, gift, loss, or conversion, it may need to be converted to the appropriate transaction type.

## Audit Packets

An audit packet is a documentation bundle. Gainz can generate one with:

- Exported Excel report.
- Linked Form 8949 detail and totals.
- Holdings reconciliation.
- Current holdings lots.
- Import warnings.
- Source transaction files that are still available on disk.
- Manifest and SHA-256 hashes.
- A short methodology note.

The packet is meant to support review. It does not replace professional tax judgment.
