# Gainz

Gainz is a local, offline crypto accounting workbench for people who want to reconcile exchange CSVs without uploading financial history to a cloud tax service.

It helps import transactions, link dispositions to acquisition lots, review unresolved sends/receives, record and apply professional-directed treatments to exact sales, and export Excel reports and workpapers for professional review.

Gainz is best understood as **private offline crypto tax reconciliation**. It does not try to be a hosted tax service. It helps you turn messy exchange exports into traceable basis links, Form 8949-style rows, current holdings reconciliation, and a documentation packet you can review with a qualified tax professional without uploading your transaction history.

## OpenAI Build Week 2026

Gainz is a pre-existing open-source project. The Build Week submission evaluates the meaningful extension built after the event submission period began, not the entire prior application.

- Pre-event baseline: [`6caf421` from July 8, 2026](https://github.com/salexandert/Gainz/commit/6caf421)
- Build Week work began after July 13, 2026.
- Validated Build Week release baseline: [`905e57f`, Gainz 0.2.44](https://github.com/salexandert/Gainz/commit/905e57f)
- Public Build Week release: [Gainz v0.2.46](https://github.com/salexandert/Gainz/releases/tag/v0.2.46)

The Build Week contribution turns an unresolved missing-basis sale into an explicit professional workflow: preserve source-reported gross value, fees, and net proceeds; separate supported FIFO quantity from unresolved quantity; select a treatment for an exact disposition; preview the before/change/after Form 8949 impact; apply or reverse the treatment; and preserve calculation receipts, professional workpapers, material assumptions, and CPA handoff documents in the audit packet. This period also added stronger guided UX, packaged-release verification, and synthetic public demonstration assets.

Codex with GPT-5.6 was used as an implementation and product-review partner for code changes, browser-first workflow testing, edge-case discovery, regression tests, release QA, and documentation. The human set the product boundaries: private/offline positioning, a conservative tax posture, professional-directed treatment rather than autonomous tax advice, exact-disposition selection, and refusal to invent missing transaction history.

### Five-Minute Judge Path

1. Download and launch the current packaged build from the [Gainz download page](https://cryptogainz.store/download/).
2. Open **Import** and click **Try Missing-Basis Demo**.
3. Continue to **Declare Holdings**, enter `0` BCH, and save the remaining synthetic holdings as zero.
4. Open **Reconcile**. Gainz shows a `0.5 BCH` sale with `0.2 BCH` supported by FIFO and `0.3 BCH` still missing acquisition basis.
5. Open the Guided Review Queue, choose a synthetic professional-directed treatment, review its exact calculation impact, and apply it.
6. Open **Reports & Export**, preview the draft status and assumptions, then generate the synthetic audit packet.

The missing-basis demo uses only the synthetic file [`demo_data/coinbase_partial_basis_fee_sample.csv`](demo_data/coinbase_partial_basis_fee_sample.csv). It contains no personal or production tax data.

## What Gainz Is

- Private offline workflow: runs locally on your machine without requiring a hosted account or transaction-history upload.
- Privacy-oriented: imported files, saved revisions, reports, and audit packets stay on your machine unless you choose to share exports.
- Reconciliation-focused: designed to help explain messy crypto history, not just produce a final number.
- Professional-direction workflow: records proceeds and basis separately, requires evidence, named professional direction, a before/after preview, and explicit confirmation before an applied missing-basis treatment updates the exact sale, Form 8949 rows, readiness, and packet workpaper. Gainz does not verify professional identity or credentials.
- No inferred disposals: Gainz does not convert sends based on age, holdings differences, or an assumed quantity. A specific send must be selected and supported before it can become a disposition.
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
- Support and parser requests: [SUPPORT.md](SUPPORT.md)

The `docs/` folder is the public documentation source of truth for the app repository. The GitHub Wiki is generated from these docs. The public website lives in the separate `salexandert/Gainz-Website` repository and syncs selected screenshots, links, and guide references from this repo so website hosting stays separate from the offline app code.

## Supported Inputs

Gainz currently includes parsers or workflows for:

- Cash App CSV exports
- Coinbase CSV exports
- Coinbase Pro / GDAX fills
- Kraken and other custom CSVs through Advanced Import / Column Mapping
- Batch manual transaction entry for source-backed buys and sells that were not imported from a CSV

See the [importer coverage and economic-fields matrix](docs/importer-coverage.md) for native versus mapped workflows, fee handling, source traceability, and known limitations.

The Cash App, Coinbase, and generic CSV import path recognizes common header aliases such as `Transaction Date`, `Activity Type`, `Crypto Quantity`, `Token Symbol`, `Spot Price USD`, and `Transaction Value`, so small export format changes are less likely to break imports.

If automatic detection cannot identify the needed columns, Gainz can pause for column review so the user can choose the header row and map the required fields.

See `demo_data/` for small sample files that are safe to use for testing.

If an exchange changes its CSV columns or adds a new transaction type, open a parser request with sanitized headers and synthetic sample rows. Do not upload full exports or private transaction history. See [Support and parser requests](SUPPORT.md).

## Quick Start With Packaged Builds

Public desktop packages are linked from the website download page with version, checksum, and SmartScreen notes:

- Download page: <https://cryptogainz.store/download/>
- Windows download: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-Windows.zip>
- Windows checksum: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-Windows.zip.sha256>
- macOS download: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-macOS.zip>
- macOS checksum: <https://github.com/salexandert/Gainz/releases/latest/download/Gainz-macOS.zip.sha256>

Unzip the package and open `Gainz.exe` on Windows or `Gainz.app` on macOS. The launcher starts the local server, shows the web interface link, and keeps your transaction data on your machine.

On first run, Gainz asks you to create a local admin account in the browser. The password is hashed into the local database and is not written to a plaintext credentials file.

If you forget the local password, click **Reset Password** in the launcher. Gainz removes only the local browser-login account and returns to the first-run setup screen, where you choose a new username and password. No temporary password is created.

The Gainz password gates the local browser UI. It does not encrypt imported CSVs, XLSX saves, exports, or audit packets, which remain normal local files. See [Reset your local Gainz login](docs/guides/local-password-reset.md).

Windows may show a Microsoft Defender SmartScreen warning. Before continuing, verify that you downloaded Gainz from the official website or GitHub Releases and compare the SHA-256 checksum. See [Windows SmartScreen Warning For Gainz](docs/guides/windows-smartscreen.md).

## Developer Start From Source

Use source checkout commands only when developing or testing Gainz locally:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open:

```text
http://127.0.0.1:5000/
```

From a source checkout, you can return to local account setup with `python .\scripts\reset_admin_password.py` or by double-clicking `reset_password.bat`. Transactions, saves, evidence, exports, and audit packets remain in place.

## Common Workflow

1. Learn the cost-basis question and collect source files.
2. Start on **Dashboard** and use **Guided Reconciliation** as the control center.
3. Open **Import** from Guided Reconciliation, then use **Try Demo Data** or upload one CSV at a time.
4. Add source-backed manual rows from the collapsed **Add manual rows** section when a CSV is missing known buys or sells.
5. Continue to **Reconcile** after the source files for the review pass are loaded.
6. Declare current holdings in **Reconcile** before deeper basis work unless Guided Reconciliation points somewhere else.
7. Review import warnings, source overlaps, and transfer questions that affect the reconciliation.
8. Let Gainz apply default FIFO basis links automatically. If acquisition records still cannot be found, use the Guided Review Queue Professional Resolution Worksheet. First select a treatment, then review its exact Form 8949 impact, and only then apply it. A CPA, EA, or tax professional may direct the conservative `$0`-basis short-term fallback for only the unresolved quantity; Gainz leaves the unknown acquisition date blank, records that the assumption may overstate tax, and keeps the action reversible.
9. Open **Tax Evidence**, build the year-by-year tax evidence inventory, and confirm or mark suggested filed totals for research.
10. Open **Reports & Export**, then use **Start guided review** to work unresolved items one at a time.
11. Review packet preview, generate the workbook or audit packet, then use the packet success screen to copy the packet path, open the output folder, and review the first files.

For a complete click-by-click guide, see [Using Gainz from import to audit packet](docs/user-walkthrough.md).

## Try The Demo Data

The `demo_data/` folder contains synthetic CSVs that are safe to use for testing:

- `demo_data/cash_app_sample.csv`
- `demo_data/coinbase_sample.csv`
- `demo_data/coinbase_convert_sample.csv`
- `demo_data/coinbase_partial_basis_fee_sample.csv` for the Build Week missing-basis workflow

A good demo run is:

1. Start Gainz from the packaged app by unzipping `Gainz-Windows.zip` and opening `Gainz.exe` on Windows, or unzipping `Gainz-macOS.zip` and opening `Gainz.app` on macOS.
2. Open **Import** from Guided Reconciliation.
3. Click **Try Demo Data**, or upload each demo CSV one file at a time.
4. Click **Continue to Declare Holdings** after data loads.
5. Enter current holdings in **Reconcile**.
6. Review warnings or tax evidence when Guided Reconciliation highlights them.
7. Review the automatic FIFO result. Open **Auto Link** only to recalculate after records change or to intentionally compare another supported lot method.
8. Open **Reports & Export** and review the **Readiness Review** checklist.
9. Use **Start guided review** if the work order has open items.
10. Expand **Review Details** only when you need row-level evidence.
11. Review the audit packet preview, then generate the workbook or draft audit packet.
12. Use the packet success screen to copy the packet path or CPA summary, open the packet folder, and review `README_FIRST.md`, `PACKET_STATUS.md`, and `FOR_CPAS.md`.

To test Gainz's professional-resolution workflow directly, click **Try Missing-Basis Demo** instead. Declare BCH holdings as `0`, continue to Reconcile, and review the partially supported BCH sale in the Guided Review Queue.

The audit packet includes root `README_FIRST.md`, `PACKET_STATUS.md`, `FOR_CPAS.md`, `CPA_HANDOFF.md`, and `PRIVACY_AND_EVIDENCE_HANDLING.md` files, the Excel workbook with a visible packet status sheet, import economics, Form 8949 detail CSVs and totals, tax filing review, tax evidence inventory, suggested filed totals, reconciliation work order CSV/Markdown, professional resolution workpapers and reversible calculation receipts, unknown gap memo CSV/Markdown, holdings reconciliation, current holdings lots, active and preserved import-warning decisions, missing-basis review, source-overlap review, copied transaction source files when available, tax evidence references, explicitly selected tax evidence copies, hashes, and a methodology memo.

## Documentation

- Official website: <https://cryptogainz.store>
- Start here: <https://cryptogainz.store/start-here/>
- Download and checksums: <https://cryptogainz.store/download/>
- Privacy model: <https://cryptogainz.store/privacy/>
- Sample audit packet: <https://cryptogainz.store/sample-packet/>
- [Public site and guide hub](docs/index.md)
- [Crypto cost basis learning path](docs/guides/crypto-cost-basis-learning.md)
- [Using Gainz from import to audit packet](docs/user-walkthrough.md)
- [How Gainz calculates basis](docs/how-gainz-calculates-basis.md)
- [Importer coverage and economic fields](docs/importer-coverage.md)
- [Offline privacy and evidence handling](docs/guides/offline-privacy-and-network-transparency.md)
- [Synthetic crypto audit packet sample](docs/guides/sample-crypto-audit-packet.md)
- [What to give your CPA checklist](docs/guides/crypto-cpa-checklist.md)
- [Coinbase missing cost basis troubleshooting](docs/guides/coinbase-missing-cost-basis.md)
- [Current holdings reconciliation explainer](docs/guides/current-holdings-reconciliation.md)
- [Reset your local Gainz login](docs/guides/local-password-reset.md)
- [Support Gainz](docs/donations.md)

## Screenshots And Wiki

The GitHub wiki is generated from `docs/` and includes an inline screenshot walkthrough, guide index, and docs publishing flow:

- [Gainz wiki walkthrough](https://github.com/salexandert/Gainz/wiki)

Public screenshots are captured from synthetic demo data so they can show the first-run workflow without exposing private transaction history.

Current public screenshots live under `docs/assets/screenshots/`, including Guided Reconciliation, fee-aware Import confirmation, Reconcile, the professional treatment preview, and Reports & Export. All release-facing screenshots use synthetic data.

When a product change affects public documentation, update `docs/` first. Regenerate the GitHub Wiki from these docs, then sync selected public docs/screenshots into the separate Gainz website repository before Netlify deploys. The `Trigger Website Sync` workflow dispatches the separate website sync after relevant app/docs changes when the repository secret `WEBSITE_REPO_TOKEN` is configured.

## Support Gainz

Gainz is free to run locally. If it saves you time, helps you organize a tax review, or gives you a clearer audit packet, donations help keep the project moving without requiring a hosted service.

- Donate: <https://cash.app/$SAl3xander>
- BTC: `bc1q5ptf8aylwauthxr80x60k554c3xdv2lpe046t4`
- Website: <https://cryptogainz.store>

## Support And Parser Requests

Use GitHub issues for sanitized bug reports and parser requests:

- Parser requests should include the source name, exact header row, synthetic sample rows, and the warning Gainz showed.
- Bug reports should include the Gainz version, operating system, packaged-vs-source run mode, and redacted steps to reproduce.
- Do not post real tax files, full exchange exports, wallet addresses, account IDs, legal names, or screenshots with private financial details.

See [SUPPORT.md](SUPPORT.md) for the support checklist.

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
