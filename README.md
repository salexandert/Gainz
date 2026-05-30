# Gainz

Gainz is a local, offline crypto accounting workbench for people who want to reconcile exchange CSVs without uploading financial history to a cloud tax service.

It helps import transactions, link sells to buys, estimate cost basis, review unresolved sends/receives, and export Excel reports for documentation or CPA review.

## What Gainz Is

- Offline-first: runs locally on your machine.
- Privacy-oriented: imported files stay on your machine unless you choose to share exports.
- Reconciliation-focused: designed to help explain messy crypto history, not just produce a final number.
- Spreadsheet-friendly: exports Excel reports, Form 8949-style sheets, transaction history, and audit packets.

## What Gainz Is Not

- Gainz is not tax, legal, or financial advice.
- Gainz does not guarantee IRS-ready results without review.
- Gainz is not a hosted service and should not be exposed directly to the public internet.

Always review outputs with a qualified tax professional before filing.

## Supported Inputs

Gainz currently includes parsers or workflows for:

- Cash App CSV exports
- Coinbase CSV exports
- Coinbase Pro / GDAX fills
- Kraken/custom imports through the template workflow
- Manual transaction entry

See `demo_data/` for small sample files that are safe to use for testing.

## Quick Start From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Then open:

```text
http://127.0.0.1:5000/
```

On first run, Gainz creates a local admin account. If `GAINZ_ADMIN_PASSWORD` is not set, a one-time generated password is written to:

```text
instance/first_run_credentials.txt
```

Set these environment variables to control first-run credentials:

```powershell
$env:GAINZ_ADMIN_USERNAME="admin"
$env:GAINZ_ADMIN_PASSWORD="choose-a-local-password"
python run.py
```

## Common Workflow

1. Import transaction CSVs.
2. Review imported buys, sells, sends, and receives.
3. Run auto-linking for an asset and year.
4. Resolve unlinked sells or unexplained holdings.
5. Export the Excel report.
6. Generate an audit packet from the Export page.

## Documentation

- [How Gainz calculates basis](docs/how-gainz-calculates-basis.md)
- [Release readiness checklist](docs/release-readiness.md)

## Packaging

The first supported distribution target should be a local desktop-style build, not a hosted SaaS product. A hosted version would require a much stronger security and compliance model because it would handle sensitive tax data.

## License

MIT. See [LICENSE](LICENSE).
