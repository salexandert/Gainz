# Donation Setup

Gainz can accept donations without becoming a hosted tax-data service. The preferred path is a local desktop release with a clear support link.

## Current Support Link

- Donation page: <https://cash.app/$SAl3xander>
- BTC receive address: `bc1q5ptf8aylwauthxr80x60k554c3xdv2lpe046t4`
- Website: <https://cryptogainz.store>

The app reads donation metadata from environment variables:

```powershell
$env:GAINZ_SUPPORT_URL='https://cash.app/$SAl3xander'
$env:GAINZ_STORE_URL='https://cryptogainz.store'
$env:GAINZ_BTC_RECEIVE_ADDRESS='bc1q5ptf8aylwauthxr80x60k554c3xdv2lpe046t4'
python launcher.py
```

If the variables are not set, Gainz uses the public CryptoGainz links above.

## Where Donations Appear

- GitHub funding metadata in `.github/FUNDING.yml`
- README support section
- App sidebar
- App footer
- Home page support panel
- Desktop launcher Donate button
- README and donation docs for the BTC receive address

## Donation Launch Checklist

1. Confirm the donation page works in a private browser window.
2. Confirm the donation page names what donations support: parser fixes, audit-packet output, packaging, and documentation.
3. Build a fresh Windows executable with `scripts/build_windows_exe.ps1`.
4. Open the packaged app and verify the Donate button opens the expected page.
5. Tag a GitHub release and include the donation link in the release notes.
6. Keep donations framed as optional support, not paid tax advice.
