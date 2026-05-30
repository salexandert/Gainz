$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Gainz `
    --add-data "app;app" `
    --add-data "Templates;Templates" `
    --add-data "Tax Forms;Tax Forms" `
    --add-data "certifi;certifi" `
    --add-data "Gainz_Export_Template-DO_NOT_MODIFY.xlsx;." `
    --add-data "Import_Transactions_Template.xlsx;." `
    --hidden-import app.add_links.routes `
    --hidden-import app.add_transactions.routes `
    --hidden-import app.auto_link.routes `
    --hidden-import app.base.routes `
    --hidden-import app.export.routes `
    --hidden-import app.history.routes `
    --hidden-import app.hodl_accounting.routes `
    --hidden-import app.home.routes `
    --hidden-import app.import_transactions.routes `
    --hidden-import app.model.routes `
    --hidden-import app.setting.routes `
    --hidden-import app.stats.routes `
    launcher.py

Write-Host ""
Write-Host "Built dist\Gainz.exe"
Write-Host "Double-click Gainz.exe to start the desktop launcher."
