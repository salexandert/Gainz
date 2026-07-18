$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$projectPython = Join-Path $repoRoot "venv\Scripts\python.exe"
$python = if ($env:PYTHON) {
    $env:PYTHON
}
elseif (Test-Path -LiteralPath $projectPython) {
    $projectPython
}
else {
    "python"
}
$version = (Get-Content -LiteralPath (Join-Path $repoRoot "VERSION") -Raw).Trim()
$distDir = Join-Path $repoRoot "dist"
$packageName = "Gainz-Windows-v$version"
$packageDir = Join-Path $distDir $packageName
$versionedZip = Join-Path $distDir "$packageName.zip"
$latestZip = Join-Path $distDir "Gainz-Windows.zip"
$iconPath = Join-Path $repoRoot "gainz_logo.ico"

if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Missing Gainz icon asset: $iconPath"
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Gainz `
    --icon $iconPath `
    --add-data "VERSION;." `
    --add-data "app_version.py;." `
    --add-data "gainz_logo.ico;." `
    --add-data "gainz_logo.png;." `
    --add-data "app;app" `
    --add-data "demo_data;demo_data" `
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
    --hidden-import app.holdings_accounting.routes `
    --hidden-import app.home.routes `
    --hidden-import app.import_transactions.routes `
    --hidden-import app.model.routes `
    --hidden-import app.setting.routes `
    --hidden-import app.stats.routes `
    launcher.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE. No release package was created."
}

$exePath = Join-Path $distDir "Gainz.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "PyInstaller completed without creating the expected executable: $exePath"
}

if ($env:GAINZ_WINDOWS_PFX_BASE64) {
    if (-not $env:GAINZ_WINDOWS_PFX_PASSWORD) {
        throw "GAINZ_WINDOWS_PFX_BASE64 was provided without GAINZ_WINDOWS_PFX_PASSWORD."
    }

    $tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
    $certificatePath = Join-Path $tempRoot "gainz-code-signing.pfx"
    [System.IO.File]::WriteAllBytes($certificatePath, [Convert]::FromBase64String($env:GAINZ_WINDOWS_PFX_BASE64))
    try {
        $signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
        if (-not $signtool) {
            throw "signtool.exe was not found on this runner."
        }

        & $signtool.Source sign `
            /fd SHA256 `
            /tr "http://timestamp.digicert.com" `
            /td SHA256 `
            /f $certificatePath `
            /p $env:GAINZ_WINDOWS_PFX_PASSWORD `
            $exePath

        if ($LASTEXITCODE -ne 0) {
            throw "Windows code signing failed."
        }
        Write-Host "Signed dist\Gainz.exe"
    }
    finally {
        if (Test-Path -LiteralPath $certificatePath) {
            Remove-Item -LiteralPath $certificatePath -Force
        }
    }
}
else {
    Write-Host "No Windows code-signing certificate configured; packaging unsigned executable."
}

$resolvedDist = Resolve-Path -LiteralPath $distDir
if (-not $resolvedDist.Path.StartsWith((Resolve-Path -LiteralPath $repoRoot).Path)) {
    throw "Refusing to package outside the repository dist directory."
}

if (Test-Path -LiteralPath $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

Copy-Item -LiteralPath $exePath -Destination $packageDir
$packageReadme = Join-Path $packageDir "README.md"
Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $packageReadme
Add-Content -LiteralPath $packageReadme -Value "`nCurrent packaged version: $version"
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $repoRoot "VERSION") -Destination $packageDir

if (Test-Path -LiteralPath $versionedZip) {
    Remove-Item -LiteralPath $versionedZip -Force
}
Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $versionedZip -Force
Copy-Item -LiteralPath $versionedZip -Destination $latestZip -Force

$versionedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $versionedZip).Hash.ToLowerInvariant()
$latestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $latestZip).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$versionedZip.sha256" -Value "$versionedHash  $packageName.zip"
Set-Content -LiteralPath "$latestZip.sha256" -Value "$latestHash  Gainz-Windows.zip"

Write-Host ""
Write-Host "Built dist\Gainz.exe"
Write-Host "Packaged dist\$packageName.zip"
Write-Host "Packaged dist\Gainz-Windows.zip"
Write-Host "Double-click Gainz.exe to start the desktop launcher."
