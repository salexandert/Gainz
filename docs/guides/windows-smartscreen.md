---
title: Windows SmartScreen Warning For Gainz
description: Why Windows may show a Microsoft Defender SmartScreen warning for Gainz.exe, how to verify the download, and what the project can do to reduce the warning over time.
---

# Windows SmartScreen Warning For Gainz

Windows may show **Windows protected your PC** when you open `Gainz.exe`, with `Publisher: Unknown publisher`.

This does not mean Windows found malware in Gainz. It usually means the executable is new, unsigned, or does not yet have enough Microsoft Defender SmartScreen reputation.

## Why This Happens

Microsoft Defender SmartScreen checks downloaded apps before they run. Microsoft says SmartScreen evaluates publisher reputation and file hash reputation. A new app, a new build, an unsigned file, or a file without enough download history can show a warning even when the file is legitimate.

Gainz releases may show this warning when Windows does not yet recognize the publisher or file reputation. Use the official source and checksum steps below before deciding whether to run the file.

Microsoft references:

- [SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
- [Microsoft Defender SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/)

## Before You Run Gainz

Only proceed if you intentionally downloaded Gainz from an official source:

- [cryptogainz.store download page]({{ '/download/' | relative_url }})
- [Gainz GitHub Releases](https://github.com/salexandert/Gainz/releases)

Do not run a Gainz executable sent by email, chat, an ad, or an unrelated download site.

## Verify The Windows Download

The Windows release includes a SHA-256 checksum file.

1. Download `Gainz-Windows.zip`.
2. Download `Gainz-Windows.zip.sha256`.
3. Open PowerShell in the download folder.
4. Run:

```powershell
Get-FileHash .\Gainz-Windows.zip -Algorithm SHA256
```

5. Compare the hash output with the `.sha256` file from GitHub Releases.

If the hashes do not match, delete the file and download Gainz again from the official page.

## If The Hash Matches And You Trust The Source

If you verified the official download and want to continue:

1. In the SmartScreen window, click **More info** if that button is shown.
2. Confirm the app name is `Gainz.exe`.
3. Click **Run anyway**.

Some Windows enterprise, school, or managed devices may block this entirely. In that case, ask the device administrator to review the official download and checksum.

## What Gainz Can Do To Improve This

There is no instant switch that makes SmartScreen trust a new independent app. The project can reduce friction by improving release trust:

1. Sign Windows executables with a trusted code-signing service.
2. Keep the same signing identity across releases so publisher reputation can accumulate.
3. Timestamp signatures and avoid modifying files after signing.
4. Publish every release through official GitHub Releases and the Gainz download page.
5. Keep SHA-256 checksums attached to each release.
6. Consider Microsoft Store distribution if the project needs the most reliable way to avoid SmartScreen download warnings.

Microsoft's current developer guidance says EV certificates no longer automatically bypass SmartScreen. Signing is still important because it shows a verified publisher and allows reputation to build across releases, but new signed builds can still warn until enough reputation accumulates.

## Current Recommendation

When the warning appears, treat it as a caution prompt and verify the download before continuing:

- Verify the download source.
- Verify the checksum.
- Keep Gainz local.
- Review generated reports with a qualified tax professional before filing.

The longer-term product goal is to sign releases and keep the download flow anchored to GitHub Releases and `cryptogainz.store`.
