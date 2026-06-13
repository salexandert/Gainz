---
title: Download Gainz
description: Download the latest local Windows or macOS build of Gainz, a crypto tax audit packet and cost-basis reconciliation tool.
schema_type: SoftwareApplication
---

# Download Gainz

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

<section class="download-panel">
  <div>
    <h2>Latest macOS Build</h2>
    <p>Download the latest Gainz macOS package, unzip it, and open <code>Gainz.app</code>. The launcher starts Gainz locally and shows a button to open the web interface.</p>
    <div class="button-row">
      <a class="button" href="{{ site.macos_download_url }}">Download Gainz-macOS.zip</a>
      <a class="button-secondary" href="{{ site.macos_checksum_url }}">Download SHA-256 checksum</a>
    </div>
  </div>
  <aside class="download-meta" aria-label="macOS download details">
    <div><span>Version</span><strong>{{ site.version }}</strong></div>
    <div><span>Platform</span><strong>macOS</strong></div>
    <div><span>Data model</span><strong>Local-first</strong></div>
    <div><span>Price</span><strong>Free, donations optional</strong></div>
  </aside>
</section>

## Before You Run It

Windows may show a SmartScreen warning and macOS may show an unidentified developer warning while Gainz is young because the packages are not code-signed yet. Only download Gainz from `cryptogainz.store` or the official GitHub repository.

Gainz runs on your machine. Imported CSVs, saves, exports, and audit packets stay local unless you choose to share them.

## First Run On Windows

1. Unzip `Gainz-Windows.zip`.
2. Double-click `Gainz.exe`.
3. Keep the launcher window open while using Gainz.
4. Click **Open Gainz** in the launcher.
5. On first run, create a local admin account in the browser.

The launcher should make it clear that Gainz is running locally. Expect a small window with the local address, an **Open Gainz** button, a copy-link action, and a quit action. When the browser opens, the first screen should look like the local Gainz app, not a cloud login page.

![Gainz home after first run]({{ '/assets/screenshots/gainz-home.png' | relative_url }})
{: .screenshot-frame }

If you forget the local password, use **Reset Password** in the launcher. This resets the local admin account to a temporary password so you can sign in and change it from the gear menu. See [Reset Your Local Gainz Password]({{ '/guides/local-password-reset/' | relative_url }}).

## First Run On macOS

1. Unzip `Gainz-macOS.zip`.
2. Open `Gainz.app`.
3. Keep the launcher window open while using Gainz.
4. Click **Open Gainz** in the launcher.
5. On first run, create a local admin account in the browser.

If you forget the local password, use **Reset Password** in the launcher. This resets the local admin account to a temporary password so you can sign in and change it from the gear menu.

## Verify The Download

The release includes SHA-256 checksum files. Advanced users can verify the Windows zip in PowerShell:

```powershell
Get-FileHash .\Gainz-Windows.zip -Algorithm SHA256
```

Compare the hash with `Gainz-Windows.zip.sha256`.

Advanced users can verify the macOS zip in Terminal:

```bash
shasum -a 256 Gainz-macOS.zip
```

Compare the hash with `Gainz-macOS.zip.sha256`.

## Important

Gainz is documentation support for crypto tax review. It is not tax, legal, or financial advice. Review outputs with a qualified tax professional before filing.
