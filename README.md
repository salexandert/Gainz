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

## Where To Start

- Website: <https://cryptogainz.store>
- GitHub Wiki walkthrough: <https://github.com/salexandert/Gainz/wiki>
- Repo docs and guides: [docs/](docs/)
- Click-by-click app walkthrough: [docs/user-walkthrough.md](docs/user-walkthrough.md)
- Crypto cost basis learning guide: [docs/guides/crypto-cost-basis-learning.md](docs/guides/crypto-cost-basis-learning.md)

The website and GitHub repository are maintained separately. The website should point visitors to the GitHub Wiki for the visual walkthrough, while the repository keeps the longer Markdown guides in `docs/`.

## Supported Inputs

Gainz currently includes parsers or workflows for:

- Cash App CSV exports
- Coinbase CSV exports
- Coinbase Pro / GDAX fills
- Kraken/custom imports through the template workflow
- Batch manual transaction entry for source-backed buys and sells that were not imported from a CSV

The Cash App, Coinbase, and generic CSV import path recognizes common header aliases such as `Transaction Date`, `Activity Type`, `Crypto Quantity`, `Token Symbol`, `Spot Price USD`, and `Transaction Value`, so small export format changes are less likely to break imports.

If automatic detection cannot identify the needed columns, Gainz can pause for column review so the user can choose the header row and map the required fields.

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

On first run, Gainz asks you to create a local admin account in the browser. The password is hashed into the local database and is not written to a plaintext credentials file.

Set these environment variables to pre-create the first local admin account instead:

```powershell
$env:GAINZ_ADMIN_USERNAME="admin"
$env:GAINZ_ADMIN_PASSWORD="choose-a-local-password"
python run.py
```

## Download Packaged Builds

Public desktop packages are published through GitHub Releases:

- Windows download: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-Windows.zip>
- Windows checksum: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-Windows.zip.sha256>
- macOS download: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-macOS.zip>
- macOS checksum: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-macOS.zip.sha256>

Unzip the package and open `Gainz.exe` on Windows or `Gainz.app` on macOS. The launcher starts the local server, shows the web interface link, and keeps your transaction data on your machine.

## Common Workflow

1. Learn the cost-basis question and collect source files.
2. Import transaction CSVs in **Import & Manage Data**.
3. Add source-backed manual rows in the batch table when a CSV is missing known buys or sells.
4. Review imported buys, sells, sends, receives, warnings, and data sources.
5. Link sells to earlier buys, usually starting with FIFO for a first review pass.
6. Declare current holdings and resolve review items.
7. Export the Excel report and audit packet from the Export page.

For a complete click-by-click guide, see [Using Gainz from import to audit packet](docs/user-walkthrough.md).

## Try The Demo Data

The `demo_data/` folder contains synthetic CSVs that are safe to use for testing:

- `demo_data/cash_app_sample.csv`
- `demo_data/coinbase_sample.csv`
- `demo_data/coinbase_convert_sample.csv`

A good demo run is:

1. Start Gainz with `python launcher.py`.
2. Open **Import & Manage Data**.
3. Click **Try Demo Data**, or upload each demo CSV one file at a time.
4. Open **Auto Link**, select each asset, and run **FIFO**.
5. Open **Holdings & Accounting** and declare current holdings for each demo asset.
6. Open **Stats & Charts** to review reconciliation and current lots.
7. Open **Export** and confirm **Audit Packet Review Status** says `Ready for review`.
8. Click **Generate Audit Packet**.

The audit packet includes the Excel workbook, Form 8949 detail CSVs, Form 8949 totals, holdings reconciliation, current holdings lots, import warnings, copied source files when available, hashes, and a methodology memo.

## Documentation

- Official website: <https://cryptogainz.store>
- [Public site and guide hub](docs/index.md)
- [Crypto cost basis learning path](docs/guides/crypto-cost-basis-learning.md)
- [Using Gainz from import to audit packet](docs/user-walkthrough.md)
- [How Gainz calculates basis](docs/how-gainz-calculates-basis.md)
- [Synthetic crypto audit packet sample](docs/guides/sample-crypto-audit-packet.md)
- [What to give your CPA checklist](docs/guides/crypto-cpa-checklist.md)
- [Coinbase missing cost basis troubleshooting](docs/guides/coinbase-missing-cost-basis.md)
- [Current holdings reconciliation explainer](docs/guides/current-holdings-reconciliation.md)
- [Support Gainz](docs/donations.md)

## Screenshots And Wiki

The GitHub wiki includes a visual walkthrough with screenshots captured from synthetic demo data:

- [Gainz wiki walkthrough](https://github.com/salexandert/Gainz/wiki)

These screenshots are meant to show the first-run workflow without exposing private transaction history.

Current public screenshots live under `docs/assets/screenshots/`, including the blank batch manual entry table used on the website and walkthrough.

## Public Site And SEO

The public website is live at <https://cryptogainz.store>. The temporary Netlify URL is <https://gainzstore.netlify.app/> while DNS and caches settle.

The `docs/` folder remains the source for project guides and SEO-oriented documentation. It includes:

- A local-first landing page.
- Focused guides for Cash App, Coinbase, Coinbase Convert, Form 8949 audit packets, and private local crypto tax software.
- Page titles, meta descriptions, canonical URLs, Open Graph metadata, a crawler-friendly sitemap, and `robots.txt`.

The public docs focus on specific reconciliation problems such as Cash App CSVs, Coinbase imports, Coinbase Convert rows, Form 8949 audit packets, and current holdings review.

The website also includes a public learning path for crypto cost basis that links to external educational material and then routes users into the Gainz import, reconciliation, and audit packet workflow.

## Analytics And Discovery

Use privacy-friendly aggregate tracking rather than user-level app telemetry:

- Website traffic: Netlify Web Analytics is enabled for `cryptogainz.store`.
- SEO: verify `cryptogainz.store` in Google Search Console and submit `https://cryptogainz.store/sitemap.xml`.
- GitHub visits: use [GitHub repository Traffic](https://github.com/salexandert/Gainz/graphs/traffic) for views, clones, referrers, and popular paths. The website GitHub nav link includes UTM tags so traffic from the site is easier to identify.
- Downloads: GitHub Release assets expose download counts for `Gainz-Windows.zip`, `Gainz-macOS.zip`, and checksums.

To check GitHub release downloads from the command line:

```powershell
python .\scripts\github_metrics.py
```

To include private repository traffic endpoints, create a GitHub token with access to the repository and run:

```powershell
$env:GITHUB_TOKEN="github_pat_..."
python .\scripts\github_metrics.py
```

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

Gainz is distributed as a local desktop-style build, not a hosted SaaS product. A hosted version would require a separate security and compliance model because it would handle sensitive tax data.

## Versioning

`VERSION` is the source of truth for releases. Keep `VERSION`, `app_version.py`, and `docs/_config.yml` in sync by running:

```powershell
.\scripts\set_version.ps1 0.2.0
```

Public releases are created from Git tags. After merging a version bump to `main`, the `Auto Tag Release Version` workflow creates the matching tag such as `v0.2.0`. That tag triggers the release workflow, which validates that the tag and version files match, builds Windows and macOS packages, verifies the release zips and checksums, then publishes them to GitHub Releases. The website download buttons point at GitHub's latest release assets, so they update when the release publishes.

For a clickable Windows build, install PyInstaller in the build environment and run:

```powershell
pip install pyinstaller
.\scripts\build_windows_exe.ps1
```

The script creates `dist\Gainz.exe`, a versioned zip such as `dist\Gainz-Windows-v0.2.0.zip`, a stable `dist\Gainz-Windows.zip`, and SHA-256 checksum files. `Gainz.exe` starts the local server in the background, shows a window confirming that Gainz is running, and provides a button to open the web interface.

For a macOS build, run this on macOS:

```bash
python3 -m pip install pyinstaller
bash scripts/build_macos_app.sh
```

The script creates `dist/Gainz.app`, a versioned zip such as `dist/Gainz-macOS-v0.2.0.zip`, a stable `dist/Gainz-macOS.zip`, and SHA-256 checksum files.

To verify packaged artifacts after a local build:

```powershell
python scripts/test_release_artifacts.py --platform windows --version 0.2.0
```

```bash
python3 scripts/test_release_artifacts.py --platform macos --version 0.2.0
```

## License

MIT. See [LICENSE](LICENSE).
