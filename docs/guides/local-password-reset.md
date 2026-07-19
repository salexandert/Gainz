---
title: Reset Your Local Gainz Login
description: Return Gainz to local account setup when you forget the browser-login password.
---

# Reset Your Local Gainz Login

Gainz has a local browser login so someone casually opening the app cannot immediately use the web interface. It is not file encryption and it is not the main protection for your tax records.

Resetting the login does not assign a temporary or default password. It removes the local browser-login account and returns Gainz to the same setup screen shown on first run. You choose a new username and password there.

## Reset From The Launcher

1. Open the Gainz launcher.
2. Click **Reset Password**.
3. Confirm that you want to reset the local login.
4. Open or reload Gainz in the browser.
5. On **Create Local Admin**, choose a username and a password with at least eight characters.

The username starts as `admin`, but you can replace it with another local username before creating the account.

If Gainz was already open in a browser, the old session will stop working because its local login account no longer exists. Reload the page to reach account setup.

## Reset From A Source Checkout

From a Windows source checkout, double-click:

```text
reset_password.bat
```

Or run:

```powershell
python .\scripts\reset_admin_password.py
```

Then start or reload Gainz. The login page will ask you to choose a new local username and password. The reset command does not print, store, or create a temporary password.

## What This Does

- Removes Gainz local browser-login accounts.
- Requires local account setup at the next login.
- Keeps imported transactions, source files, saves, evidence records, exports, and audit packets in place.
- Overrides an environment-configured bootstrap password until you complete account setup in the browser.

## What This Does Not Do

- It does not delete transaction or tax records.
- It does not encrypt imported files, saves, exports, or audit packets.
- It does not protect files from someone who already has access to your Windows or macOS user account.
- It does not create a cloud account, email recovery flow, hosted password reset, or default password.

Many Gainz outputs are normal `.xlsx`, `.csv`, `.json`, and `.txt` files that desktop tools can open. Protect the computer, operating-system account, synced folders, backups, and export folders as you would any other sensitive tax documents.
