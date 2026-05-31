---
title: Download Gainz For Windows
description: Download the latest local Windows build of Gainz, a crypto tax audit packet and cost-basis reconciliation tool.
schema_type: SoftwareApplication
---

# Download Gainz For Windows

<section class="download-panel">
  <div>
    <h2>Latest Windows Build</h2>
    <p>Download the latest Gainz Windows package, unzip it, and double-click <code>Gainz.exe</code>. The launcher starts Gainz locally and shows a button to open the web interface.</p>
    <div class="button-row">
      <a class="button" href="{{ site.download_url }}">Download Gainz-Windows.zip</a>
      <a class="button-secondary" href="{{ site.checksum_url }}">Download SHA-256 checksum</a>
    </div>
  </div>
  <aside class="download-meta" aria-label="Download details">
    <div><span>Version</span><strong>{{ site.version }}</strong></div>
    <div><span>Platform</span><strong>Windows</strong></div>
    <div><span>Data model</span><strong>Local-first</strong></div>
    <div><span>Price</span><strong>Free, donations optional</strong></div>
  </aside>
</section>

## Before You Run It

Windows may show a SmartScreen warning while Gainz is young because the executable is not code-signed yet. Only download Gainz from `cryptogainz.store` or the official GitHub repository.

Gainz runs on your machine. Imported CSVs, saves, exports, and audit packets stay local unless you choose to share them.

## First Run

1. Unzip `Gainz-Windows.zip`.
2. Double-click `Gainz.exe`.
3. Keep the launcher window open while using Gainz.
4. Click **Open Gainz** in the launcher.
5. If first-run credentials are generated, the launcher shows where they were saved.

## Verify The Download

The release includes a SHA-256 checksum file. Advanced users can verify it in PowerShell:

```powershell
Get-FileHash .\Gainz-Windows.zip -Algorithm SHA256
```

Compare the hash with `Gainz-Windows.zip.sha256`.

## Important

Gainz is documentation support for crypto tax review. It is not tax, legal, or financial advice. Review outputs with a qualified tax professional before filing.
