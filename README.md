
---

# Gainz – Private, Offline Crypto Accounting

**Gainz** is a fully offline, privacy-first crypto accounting app. It helps you import your exchange transaction history and walk through common scenarios to gain insight into your holdings and estimate capital gains or losses.

No internet connection is required—your data stays on your machine.

---

## ✨ Key Features

* **Offline-first:** All data processing happens locally—no tracking, no cloud storage.
* **CSV Import:** Load your transaction history from supported exchanges or a custom template.
* **Simplified Accounting:** Uses a Universal Wallet approach—no need for full blockchain history or wallet xpubs.
* **Cost Basis Calculation:** Gainz links buys and sells across wallets and exchanges, even if assets never moved between them.
* **Discrepancy Detection:** Helps identify missing transactions (e.g. lost, gifted, converted) and offers suggestions to resolve them.
* **Export Reports:** Output Excel-based reports for documentation and sharing.

---

## 🧠 How It Works

Gainz uses the **Universal Wallet Method** for accounting. This allows you to:

* Track transactions regardless of the wallet or exchange.
* Link sells to buys—even without blockchain transfer data.
* Focus only on **taxable events**, not every coin movement.

For example, if your imported data shows you bought **3 BTC**, sold **1 BTC**, and still hold **1 BTC**, then Gainz flags a **discrepancy**—you likely gifted, lost, or converted the remaining 1 BTC. You can either:

* Manually add the missing transaction, or
* Let Gainz auto-suggest a matching "sell" or "lost" record.

You can also include **off-exchange events**, like converting ETH to BTC via ShapeShift, to improve accuracy.

---

## 🚀 Getting Started

1. **Launch the App**
   Run `GainzApp.exe`. A command prompt window will open—leave it open while using Gainz.

2. **Access in Browser**
   Visit `http://127.0.0.1:5000/` in your web browser.
   Login using:

   * **Username:** `admin`
   * **Password:** `admin`

3. **Import Transactions**
   Gainz supports CSV files from:

   * Coinbase
   * Coinbase Pro
   * Kraken
   * Cash App

   For unsupported sources, use the included
   **`Import_Transactions_Template.xlsx`**, or manually enter transactions via the **Manage Transactions** page.

---

## 🛠 Download & Run

### ✅ Compiled Version (Windows)

Download from Google Drive:
[https://drive.google.com/drive/folders/1YLyRRWitJ1pHVVMHnspB783Pq52DWUnC?usp=share_link](https://drive.google.com/drive/folders/1YLyRRWitJ1pHVVMHnspB783Pq52DWUnC?usp=share_link)

### 🧪 Or compile it Yourself

To compile from source using `pyinstaller`, run:

```bash
pyinstaller --add-data "app;app" --onefile \
  --hidden-import flask_wtf \
  --hidden-import bcrypt \
  --hidden-import wtforms.fields.html5 \
  --hidden-import utils \
  --hidden-import cffi \
  --icon="C:{path repo}\gainz_logo.ico" \
  run.py
```

---

## 💸 Donations Welcome

If Gainz helped you, consider supporting the project:

* **Bitcoin:** `bc1qm0sykhxhhqey9yg2t93mqp4jzgdl88ewa82q3s`
* **CashApp:** `$SAl3xander`

Your support is deeply appreciated 🙏

---

## ⚠️ Disclaimer

> **Gainz does not provide legal, financial, or tax advice.**
> Please consult with certified professionals to validate all outputs before filing taxes or making financial decisions.

---

## ❤️ Thanks

Thank you for your interest and support.
I hope Gainz is exactly what you were looking for!

---
