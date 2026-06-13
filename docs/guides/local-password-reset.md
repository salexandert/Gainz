---
title: Reset Your Local Gainz Password
description: How to reset the local Gainz admin password and understand what the local password does and does not protect.
---

# Reset Your Local Gainz Password

Gainz has a local browser login so someone casually opening the app cannot immediately use the web interface. It is not file encryption and it is not meant to be the main protection for your tax records.

Your imported CSVs, saves, exports, and audit packets are local files. Many of the outputs are `.xlsx`, `.csv`, `.json`, and `.txt` files that can be opened by normal desktop tools. Protect the computer, user account, OneDrive folder, backups, and export folders the same way you would protect any other sensitive tax documents.

## Reset From The Launcher

1. Open the Gainz launcher.
2. Click **Reset Password**.
3. Confirm the reset.
4. Sign in with:

```text
Username: admin
Temporary password: gainz-local-reset
```

5. Open the gear menu in the top right.
6. Click **Change Password**.
7. Set a new local password.

If you configured a different admin username with `GAINZ_ADMIN_USERNAME`, the reset uses that configured username instead of `admin`.

## Reset From A Source Checkout

If you are running Gainz from source, close Gainz first, then run:

```powershell
python .\scripts\reset_admin_password.py
```

On Windows source checkouts, you can also double-click:

```text
reset_password.bat
```

The command resets the configured local admin account to:

```text
Temporary password: gainz-local-reset
```

Then start Gainz again, sign in, and change the password from the gear menu.

## What This Does

- Updates the local admin password hash in the local Gainz database.
- Creates the local admin account if it does not exist yet.
- Keeps your imported files, saves, exports, and audit packets in place.

## What This Does Not Do

- It does not encrypt your transaction files.
- It does not encrypt Gainz exports or audit packets.
- It does not protect files from someone who already has access to your Windows or macOS user account.
- It does not create a cloud account, email recovery flow, or hosted password reset.

For sensitive real records, rely on operating system account security, disk encryption, careful backup handling, and private storage locations.
