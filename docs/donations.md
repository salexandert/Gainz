---
title: Support Gainz
description: Optional ways to support Gainz, a free local-first crypto tax documentation tool.
---

# Support Gainz

Gainz is free to run locally. Donations are optional and help support parser fixes, packaging, documentation, and continued development.

## Donation Links

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

Donations are not payment for tax, legal, financial, accounting, or filing advice.
