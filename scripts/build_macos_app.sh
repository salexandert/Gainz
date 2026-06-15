#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON:-python3}"
version="$(tr -d '[:space:]' < VERSION)"
dist_dir="$repo_root/dist"
package_name="Gainz-macOS-v$version"
package_dir="$dist_dir/$package_name"
versioned_zip="$dist_dir/$package_name.zip"
latest_zip="$dist_dir/Gainz-macOS.zip"

"$python_bin" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name Gainz \
  --add-data "VERSION:." \
  --add-data "app_version.py:." \
  --add-data "gainz_logo.ico:." \
  --add-data "gainz_logo.png:." \
  --add-data "app:app" \
  --add-data "demo_data:demo_data" \
  --add-data "Templates:Templates" \
  --add-data "Tax Forms:Tax Forms" \
  --add-data "certifi:certifi" \
  --add-data "Gainz_Export_Template-DO_NOT_MODIFY.xlsx:." \
  --add-data "Import_Transactions_Template.xlsx:." \
  --hidden-import app.add_links.routes \
  --hidden-import app.add_transactions.routes \
  --hidden-import app.auto_link.routes \
  --hidden-import app.base.routes \
  --hidden-import app.export.routes \
  --hidden-import app.history.routes \
  --hidden-import app.holdings_accounting.routes \
  --hidden-import app.home.routes \
  --hidden-import app.import_transactions.routes \
  --hidden-import app.model.routes \
  --hidden-import app.setting.routes \
  --hidden-import app.stats.routes \
  launcher.py

mkdir -p "$dist_dir"
rm -rf "$package_dir"
mkdir -p "$package_dir"

cp -R "$dist_dir/Gainz.app" "$package_dir/"
cp README.md LICENSE VERSION "$package_dir/"

rm -f "$versioned_zip" "$latest_zip"
(
  cd "$dist_dir"
  ditto -c -k --sequesterRsrc --keepParent "$package_name" "$package_name.zip"
  cp "$package_name.zip" "Gainz-macOS.zip"
)

versioned_hash="$(shasum -a 256 "$versioned_zip" | awk '{print tolower($1)}')"
latest_hash="$(shasum -a 256 "$latest_zip" | awk '{print tolower($1)}')"
printf "%s  %s.zip\n" "$versioned_hash" "$package_name" > "$versioned_zip.sha256"
printf "%s  Gainz-macOS.zip\n" "$latest_hash" > "$latest_zip.sha256"

echo
echo "Built dist/Gainz.app"
echo "Packaged dist/$package_name.zip"
echo "Packaged dist/Gainz-macOS.zip"
echo "Open Gainz.app to start the desktop launcher."
