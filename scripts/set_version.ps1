param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

if ($Version -notmatch '^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$') {
    throw "Version must use semantic version format, for example 0.2.0."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    [System.IO.File]::WriteAllText($Path, $Content + "`n", $utf8NoBom)
}

Write-Utf8NoBom -Path (Join-Path $repoRoot "VERSION") -Content $Version
Write-Utf8NoBom -Path (Join-Path $repoRoot "app_version.py") -Content "APP_VERSION = `"$Version`""
Write-Utf8NoBom -Path (Join-Path $repoRoot "scripts\release_version.env") -Content "version=$Version`ntag=v$Version"

$docsConfigPath = Join-Path $repoRoot "docs\_config.yml"
$docsConfig = Get-Content -LiteralPath $docsConfigPath -Raw
$docsConfig = $docsConfig -replace '(?m)^version:\s*.+$', "version: $Version"
[System.IO.File]::WriteAllText($docsConfigPath, $docsConfig, $utf8NoBom)

Write-Host "Gainz version set to $Version"
Write-Host "Create a release by merging this change, then pushing tag v$Version."
