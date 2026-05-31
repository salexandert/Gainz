# Gainz

Gainz is a local, offline crypto accounting workbench for people who want to reconcile exchange CSVs without uploading financial history to a cloud tax service.

It helps import transactions, link sells to buys, estimate cost basis, review unresolved sends/receives, and export Excel reports for documentation or CPA review.

Gainz is best understood as a **local-first crypto tax audit packet tool**. It does not try to be a hosted tax service. It helps you turn messy exchange exports into traceable basis links, Form 8949-style rows, current holdings reconciliation, and a documentation packet you can review with a qualified tax professional.

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
python launcher.py
```

The launcher opens a small desktop window that shows the local web interface link. Click **Open Gainz** or open:

```text
http://127.0.0.1:5000/
```

For developer console output, you can still run:

```powershell
python run.py
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

## Download Packaged Build

The public Windows package is published through GitHub Releases:

- Latest download: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-Windows.zip>
- Checksum: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-Windows.zip.sha256>

Unzip the package and double-click `Gainz.exe`. The launcher starts the local server, shows the web interface link, and keeps your transaction data on your machine.

## Common Workflow

1. Import transaction CSVs.
2. Review imported buys, sells, sends, and receives.
3. Run auto-linking for an asset and year.
4. Resolve unlinked sells or unexplained holdings.
5. Export the Excel report.
6. Generate an audit packet from the Export page.

For a complete click-by-click guide, see [Using Gainz from import to audit packet](docs/user-walkthrough.md).

## Try The Demo Data

The `demo_data/` folder contains synthetic CSVs that are safe to use for testing:

- `demo_data/cash_app_sample.csv`
- `demo_data/coinbase_sample.csv`
- `demo_data/coinbase_convert_sample.csv`

A good demo run is:

1. Start Gainz with `python launcher.py`.
2. Open **Import Transactions**.
3. Upload each demo CSV one file at a time.
4. Open **Auto Link**, select each asset, and run **FIFO**.
5. Open **Holdings & Accounting** and declare current holdings for each demo asset.
6. Open **Stats & Charts** to review reconciliation and current lots.
7. Open **Export** and confirm **Audit Readiness** says `Ready`.
8. Click **Generate Audit Packet**.

The audit packet includes the Excel workbook, Form 8949 detail CSVs, Form 8949 totals, holdings reconciliation, current holdings lots, import warnings, copied source files when available, hashes, and a methodology memo.

## Documentation

- [Public site and guide hub](docs/index.md)
- [Using Gainz from import to audit packet](docs/user-walkthrough.md)
- [How Gainz calculates basis](docs/how-gainz-calculates-basis.md)
- [SEO launch roadmap](docs/seo-roadmap.md)
- [Product improvement notes](docs/product-improvement-notes.md)
- [Release readiness checklist](docs/release-readiness.md)
- [Donation setup](docs/donations.md)

## Public Site And SEO

The `docs/` folder is ready to publish as a GitHub Pages site or a static site at <https://cryptogainz.store>. It includes:

- A local-first landing page.
- Focused guides for Cash App, Coinbase, Coinbase Convert, Form 8949 audit packets, and private local crypto tax software.
- Page titles, meta descriptions, canonical URLs, Open Graph metadata, a crawler-friendly sitemap, and `robots.txt`.

The best early SEO strategy is useful, specific documentation for people trying to reconcile crypto CSVs, not generic crypto-tax content. Start with the guide pages, then add screenshots, release downloads, and synthetic demo outputs as the product becomes easier for first-time users.

## Support Gainz

Gainz is free to run locally. If it saves you time, helps you organize a tax review, or gives you a clearer audit packet, donations help keep the project moving without requiring a hosted service.

- Donate: <https://cash.app/$SAl3xander>
- BTC: `bc1q5ptf8aylwauthxr80x60k554c3xdv2lpe046t4`
- Website: <https://cryptogainz.store>

For custom builds or forks, set these environment variables before starting Gainz:

```powershell
$env:GAINZ_SUPPORT_URL="https://your-donation-link.example"
$env:GAINZ_STORE_URL="https://your-project-site.example"
$env:GAINZ_BTC_RECEIVE_ADDRESS="your-btc-address"
python launcher.py
```

## Packaging

The first supported distribution target should be a local desktop-style build, not a hosted SaaS product. A hosted version would require a much stronger security and compliance model because it would handle sensitive tax data.

## Versioning

`VERSION` is the source of truth for releases. Keep `VERSION`, `app_version.py`, and `docs/_config.yml` in sync by running:

```powershell
.\scripts\set_version.ps1 0.2.0
```

Public releases are created from Git tags. After merging a version bump, push a matching tag such as `v0.2.0`. The release workflow validates that the tag and version files match before publishing.

For a clickable Windows build, install PyInstaller in the build environment and run:

```powershell
pip install pyinstaller
.\scripts\build_windows_exe.ps1
```

The script creates `dist\Gainz.exe`, a versioned zip such as `dist\Gainz-Windows-v0.2.0.zip`, a stable `dist\Gainz-Windows.zip`, and SHA-256 checksum files. `Gainz.exe` starts the local server in the background, shows a window confirming that Gainz is running, and provides a button to open the web interface.

## License

MIT. See [LICENSE](LICENSE).
