# Support And Parser Requests

Gainz is a private offline crypto reconciliation tool. Please keep that privacy model when asking for help.

## Before Posting

Do not post:

- real tax returns, Form 8949 files, payment receipts, or audit packets
- full exchange CSV exports
- wallet addresses, transaction IDs, account IDs, legal names, emails, or phone numbers
- screenshots that show private balances, source folders, or tax folders

Do post:

- Gainz version and operating system
- whether you used the packaged app or source checkout
- the exact warning or error text
- sanitized screenshots with private data removed
- synthetic CSV headers and 2-5 fake rows that preserve the export format

## Parser Requests

Use the **Parser or CSV Support Request** issue template when an exchange export changed column names, has a new row type, or cannot be detected.

Good parser requests include:

- exchange or source name
- exact header row
- 2-5 synthetic rows that preserve dates, types, assets, quantities, USD columns, and notes
- what each row should mean in Gainz, such as buy, sell, send, receive, convert, reward, fee, or owner transfer
- the warning or skipped-row message Gainz showed

Do not attach the original CSV. If a sample file is needed, create a tiny synthetic CSV that has the same columns but no real transactions.

## Bug Reports

Use the **Bug Report** issue template for app crashes, confusing workflow states, export issues, release package problems, or privacy concerns.

For packaged app issues, include whether the launcher window opened, whether `http://127.0.0.1:5000/healthz` responded, and whether another app was already using port 5000.

## Security Or Privacy Concerns

Do not open a public issue with sensitive details. Use GitHub private vulnerability reporting if available for this repository, or contact the maintainer through a private channel first.
