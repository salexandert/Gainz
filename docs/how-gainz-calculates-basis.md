# How Gainz Calculates Basis

If you are new to cost basis, start with the [crypto cost basis learning path]({{ '/guides/crypto-cost-basis-learning/' | relative_url }}). It explains the user flow before getting into Gainz-specific mechanics.

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

For general education, the [Gordon Law crypto cost basis guide](https://gordonlaw.com/learn/crypto-cost-basis/) is a helpful plain-language overview of cost basis concepts. For official federal tax framing, review the [IRS virtual currency FAQs](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions) and discuss your specific facts with a qualified tax professional.

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

If a receive is really an acquisition, it may need to be converted to a buy with basis. If a send is really a documented sale, exchange, payment, fee, gift, or other transfer of ownership, it may need to be recorded as a taxable disposal. If the send was only a transfer between accounts you own or control, it should stay as a transfer and should not be recorded as a disposal.

The IRS digital assets page says that transferring digital assets between wallets or accounts you own or control is generally not a reportable digital asset transaction unless you paid a transaction fee with digital assets. It also says sales, exchanges, payments, transfer fees, and transfers of ownership or financial interest are digital asset transactions. See the [IRS digital assets page](https://www.irs.gov/filing/digital-assets) for the current federal framing.

Gainz treats send and receive rows as classification questions. The **Reconcile** page shows a Transfer Classification Review table for the selected asset:

- A nearby same-quantity send and receive can be a clue for an owner transfer, but the user still needs source records to confirm it.
- A send without a matching receive may indicate an owner transfer to a wallet that has not been imported, or it may be a documented disposal, fee, gift, loss, or other ownership transfer.
- A receive without a matching send may indicate a buy from another exchange, income, rewards, gift, or a transfer from an unimported wallet.
- Classification changes should be based on records, not on making the reconciliation number look better.

## Loss Review

Gainz can mark a lot for loss review when source records show an asset may be lost, stolen, abandoned, or otherwise no longer owned. This is a documentation step, not a filing conclusion.

Loss treatment depends on the facts. The [Taxpayer Advocate Service digital asset loss guide](https://www.taxpayeradvocate.irs.gov/news/tax-tips/tas-tax-tip-when-can-you-deduct-digital-asset-investment-losses/2023/10/) explains that frozen accounts, bankruptcy, worthless assets, abandonment, and theft can have different tax treatment. [IRS Topic 515](https://www.irs.gov/taxtopics/tc515) explains that theft losses must meet specific requirements and may be reported on Form 4684 when allowed. Review loss items with a qualified tax professional before relying on them in generated reports.

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
