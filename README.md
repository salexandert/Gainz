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

The `docs/` folder is the public documentation source of truth for the app repository. The GitHub Wiki is generated from these docs. The public website lives in the separate `salexandert/Gainz-Website` repository and syncs selected screenshots, links, and guide references from this repo so website hosting stays separate from the local-first app code.

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

If you forget the local password, click **Reset Password** in the launcher. It resets the configured local admin account to the temporary password `gainz-local-reset` so you can sign in and set a new password from the gear menu. From a source checkout, you can also run `python .\scripts\reset_admin_password.py` or double-click `reset_password.bat`.

The Gainz password gates the local browser UI. It does not encrypt imported CSVs, XLSX saves, exports, or audit packets, which remain normal local files. See [Reset your local Gainz password](docs/guides/local-password-reset.md).

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

Windows may show a Microsoft Defender SmartScreen warning while Gainz is young and unsigned. Before clicking through that warning, verify that you downloaded Gainz from the official website or GitHub Releases and compare the SHA-256 checksum. See [Windows SmartScreen Warning For Gainz](docs/guides/windows-smartscreen.md).

## Common Workflow

1. Learn the cost-basis question and collect source files.
2. Start on **Dashboard** and use it as the control center.
3. Import transaction CSVs in **Import**.
4. Add source-backed manual rows in the batch table when a CSV is missing known buys or sells.
5. Return to **Dashboard** and follow **Continue reconciliation**.
6. Declare current holdings in **Reconcile** before deeper basis work unless Dashboard points somewhere else.
7. Review import warnings, source overlaps, and transfer questions that affect the reconciliation.
8. Run FIFO or another basis-linking review in **Auto Link** when Dashboard or Reports & Export says sales still need basis.
9. Open **Tax Evidence**, build the year-by-year tax evidence inventory, and confirm or mark suggested filed totals for research.
10. Open **Reports & Export**, review readiness, expand **Review Details** only when needed, and generate the workbook or audit packet.

For a complete click-by-click guide, see [Using Gainz from import to audit packet](docs/user-walkthrough.md).

## Try The Demo Data

The `demo_data/` folder contains synthetic CSVs that are safe to use for testing:

- `demo_data/cash_app_sample.csv`
- `demo_data/coinbase_sample.csv`
- `demo_data/coinbase_convert_sample.csv`

A good demo run is:

1. Start Gainz with `python launcher.py`.
2. Open **Import**.
3. Click **Try Demo Data**, or upload each demo CSV one file at a time.
4. Return to **Dashboard** and follow **Continue reconciliation**.
5. Enter current holdings in **Reconcile**.
6. Review warnings or tax evidence if Dashboard shows them.
7. Run **FIFO** in **Auto Link** only when Dashboard or Reports & Export says basis links are blocking readiness.
8. Open **Reports & Export** and review the **Readiness Review** checklist.
9. Expand **Review Details** only when you need row-level evidence.
10. Review the audit packet preview, then generate the workbook or draft audit packet.

The audit packet includes root `README_FIRST.md` and `PACKET_STATUS.md` files, the Excel workbook with a visible packet status sheet, Form 8949 detail CSVs, Form 8949 totals, tax filing review, tax evidence inventory, suggested filed totals, reconciliation work order CSV/Markdown, holdings reconciliation, current holdings lots, active and preserved import-warning decisions, missing-basis review, source-overlap review, copied transaction source files when available, tax evidence references, explicitly selected tax evidence copies, hashes, and a methodology memo.

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
- [Reset your local Gainz password](docs/guides/local-password-reset.md)
- [Support Gainz](docs/donations.md)

## Screenshots And Wiki

The GitHub wiki is generated from `docs/` and includes an inline screenshot walkthrough, guide index, and docs publishing flow:

- [Gainz wiki walkthrough](https://github.com/salexandert/Gainz/wiki)

Public screenshots are captured from synthetic demo data so they can show the first-run workflow without exposing private transaction history.

Current public screenshots live under `docs/assets/screenshots/`, including Dashboard, Import, Reconcile, Reports & Export, advanced Stats & Charts, Model Sell, and blank batch manual entry screens captured from synthetic demo data.

When a product change affects public documentation, update `docs/` first. Regenerate the GitHub Wiki from these docs, then sync selected public docs/screenshots into the separate Gainz website repository before Netlify deploys.

## Public Site And SEO

The public website is live at <https://cryptogainz.store>. The site is tracked separately in `salexandert/Gainz-Website`, but most public documentation changes should still start in this repository's `docs/` folder so the app docs and wiki remain the source of truth.

The `docs/` folder remains the source for project guides and SEO-oriented documentation. It includes:

- A local-first landing page.
- Focused guides for Cash App, Coinbase, Coinbase Convert, Form 8949 audit packets, and private local crypto tax software.
- Page titles, meta descriptions, canonical URLs, Open Graph metadata, a crawler-friendly sitemap, and `robots.txt`.

The public docs focus on specific reconciliation problems such as Cash App CSVs, Coinbase imports, Coinbase Convert rows, Form 8949 audit packets, and current holdings review.

The website also includes a public learning path for crypto cost basis that links to external educational material and then routes users into the Gainz import, reconciliation, and audit packet workflow.

For contributor workflow details, see [CONTRIBUTING.md](CONTRIBUTING.md).

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

Public releases are created from Git tags. After merging a version bump to `main`, the `Auto Tag Release Version` workflow creates the matching tag such as `v0.2.0` and dispatches the release workflow for that tag. The release workflow validates that the tag and version files match, builds Windows and macOS packages, verifies the release zips and checksums, publishes them to GitHub Releases, then downloads the published Windows ZIP by tag to verify the public package. The website download buttons point at GitHub's latest release assets, so they update when the release publishes.

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

To verify the public Windows ZIP after a release publishes:

```powershell
python scripts/test_downloaded_release_zip.py --version 0.2.0 --tag v0.2.0
```

For a manual packaged-launch smoke test, first stop any local Gainz process on port 5000, then run:

```powershell
python scripts/test_downloaded_release_zip.py --version 0.2.0 --tag v0.2.0 --launch
```

## License

MIT. See [LICENSE](LICENSE).
