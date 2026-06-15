import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
DEFAULT_SITE_URL = "https://cryptogainz.store"
REPO_URL = "https://github.com/salexandert/Gainz"
RAW_REPO_URL = "https://raw.githubusercontent.com/salexandert/Gainz/main"

ROOT_DOCS = [
    "download.md",
    "user-walkthrough.md",
    "how-gainz-calculates-basis.md",
    "donations.md",
]

SCREENSHOTS = [
    (
        "Reconciliation Dashboard",
        "gainz-home.png",
        "Dashboard shows the readiness summary, next action, and review queue.",
    ),
    (
        "Import",
        "gainz-import-manage-data.png",
        "Import source CSVs, try demo data, add manual batches, review data sources, and inspect revisions.",
    ),
    (
        "Manual batch entry",
        "gainz-manual-batch-entry.png",
        "Manual rows let users enter known buys or sells that were not present in imported CSV files.",
    ),
    (
        "Reconcile holdings",
        "gainz-holdings-accounting.png",
        "Current holdings reconciliation helps users compare declared holdings against imported activity.",
    ),
    (
        "Advanced stats and charts",
        "gainz-stats-charts.png",
        "Stats and Charts remains available for deeper asset-level inspection after Dashboard identifies what to review.",
    ),
    (
        "Model a sale",
        "gainz-model-sell.png",
        "Model Sell estimates proceeds, basis, and gain or loss for a hypothetical sale.",
    ),
    (
        "Reports and Export readiness",
        "gainz-export-audit-readiness.png",
        "Reports and Export summarizes readiness, output location, file generation, and collapsed review details.",
    ),
]

GENERATED_PAGES = {
    "Home.md",
    "Using-Gainz-From-Import-To-Audit-Packet.md",
    "Guides.md",
    "Docs-And-Website-Publishing.md",
}


def _config_value(name, default=""):
    config_path = DOCS_ROOT / "_config.yml"
    if not config_path.exists():
        return default

    prefix = f"{name}:"
    for line in config_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            return value or default
    return default


def _front_matter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    metadata = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def _strip_front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip()
    return text


def _title_from_path(path):
    metadata = _front_matter(path)
    if metadata.get("title"):
        return metadata["title"]

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()

    return path.stem.replace("-", " ").title()


def _site_url_for(path, site_url):
    relative = path.relative_to(DOCS_ROOT)
    if relative.name == "index.md":
        if len(relative.parts) == 1:
            route = "/"
        else:
            route = "/" + "/".join(relative.parts[:-1]) + "/"
    else:
        route = "/" + "/".join(relative.with_suffix("").parts) + "/"
    return f"{site_url.rstrip('/')}{route}"


def _asset_url(asset_path, site_url):
    return f"{RAW_REPO_URL}/docs/assets/{asset_path.lstrip('/')}"


def _relative_url(path, site_url):
    if path.startswith("/assets/"):
        return f"{RAW_REPO_URL}/docs{path}"

    return f"{site_url.rstrip('/')}{path}"


def _screenshot_url(filename, site_url):
    return _asset_url(f"screenshots/{filename}", site_url)


def _link_line(path, site_url):
    title = _title_from_path(path)
    return f"- [{title}]({_site_url_for(path, site_url)})"


def _guide_paths():
    return sorted(
        (DOCS_ROOT / "guides").glob("*.md"),
        key=lambda path: _title_from_path(path).lower(),
    )


def _generated_header(page_name):
    return "\n".join(
        [
            "<!-- This page is generated from docs/ by scripts/generate_wiki_home.py. -->",
            "<!-- Update docs/ in the main repository; do not hand-edit this generated wiki page. -->",
            f"<!-- Generated page: {page_name} -->",
            "",
        ]
    )


def _render_jekyll_markdown(text, site_url):
    def relative_url_replacement(match):
        path = match.group(1).strip()
        return _relative_url(path, site_url)

    text = re.sub(
        r"\{\{\s*['\"]([^'\"]+)['\"]\s*\|\s*relative_url\s*\}\}",
        relative_url_replacement,
        text,
    )

    site_values = {
        "version": _config_value("version", ""),
        "download_url": _config_value("download_url", ""),
        "checksum_url": _config_value("checksum_url", ""),
        "macos_download_url": _config_value("macos_download_url", ""),
        "macos_checksum_url": _config_value("macos_checksum_url", ""),
    }

    def site_value_replacement(match):
        value = site_values.get(match.group(1), "")
        return value or match.group(0)

    text = re.sub(r"\{\{\s*site\.([a-zA-Z0-9_]+)\s*\}\}", site_value_replacement, text)
    text = re.sub(r"^\{:\s+\.[^}]+\}\s*$", "", text, flags=re.MULTILINE)
    return text


def _wiki_link(label, page):
    return f"[[{label}|{page}]]"


def _screenshot_block(title, filename, caption, site_url):
    return "\n".join(
        [
            f"### {title}",
            "",
            f"![{title}]({_screenshot_url(filename, site_url)})",
            "",
            caption,
            "",
        ]
    )


def build_home():
    site_url = _config_value("url", DEFAULT_SITE_URL)
    version = _config_value("version", "")
    root_paths = [DOCS_ROOT / name for name in ROOT_DOCS if (DOCS_ROOT / name).exists()]
    guide_paths = _guide_paths()

    lines = [
        _generated_header("Home.md").rstrip(),
        "# Gainz Wiki",
        "",
        "Gainz is a local-first crypto tax review and audit-packet tool. The public documentation is maintained in the main repository under `docs/`, published to the website, and mirrored here as generated wiki pages.",
        "",
        f"- Public website and docs: <{site_url}>",
        f"- Main repository: <{REPO_URL}>",
        f"- Detailed walkthrough: {_wiki_link('Using Gainz From Import To Audit Packet', 'Using-Gainz-From-Import-To-Audit-Packet')}",
        f"- Guide index: {_wiki_link('Guides', 'Guides')}",
        f"- Documentation update flow: {_wiki_link('Docs And Website Publishing', 'Docs-And-Website-Publishing')}",
    ]
    if version:
        lines.append(f"- Current documented version: `{version}`")

    lines.extend(
        [
            "",
            "## Start Here",
            "",
        ]
    )
    lines.extend(_link_line(path, site_url) for path in root_paths)

    lines.extend(
        [
            "",
            "## Visual Product Walkthrough",
            "",
            "These screenshots use synthetic demo data only and are safe for public documentation.",
            "",
        ]
    )
    for title, filename, caption in SCREENSHOTS:
        lines.append(_screenshot_block(title, filename, caption, site_url).rstrip())
        lines.append("")

    lines.extend(
        [
            "## Guides",
            "",
        ]
    )
    lines.extend(_link_line(path, site_url) for path in guide_paths)

    lines.extend(
        [
            "",
            "## Important",
            "",
            "Gainz is documentation support for crypto tax review. It is not tax, legal, financial, accounting, or filing advice. Review outputs with a qualified tax professional before filing.",
            "",
        ]
    )
    return "\n".join(lines)


def build_walkthrough():
    site_url = _config_value("url", DEFAULT_SITE_URL)
    source = DOCS_ROOT / "user-walkthrough.md"
    text = source.read_text(encoding="utf-8")
    text = _strip_front_matter(text)
    text = _render_jekyll_markdown(text, site_url)

    lines = [
        _generated_header("Using-Gainz-From-Import-To-Audit-Packet.md").rstrip(),
        text.rstrip(),
        "",
        "## Live Website Version",
        "",
        f"The website version is published at <{_site_url_for(source, site_url)}>.",
        "",
    ]
    return "\n".join(lines)


def build_guides():
    site_url = _config_value("url", DEFAULT_SITE_URL)
    guide_paths = _guide_paths()

    lines = [
        _generated_header("Guides.md").rstrip(),
        "# Gainz Guides",
        "",
        "Use these public guides when you want to move from exchange CSVs to reviewable crypto tax evidence. The website is the canonical rendered version; this wiki page keeps the same guide set discoverable from GitHub.",
        "",
        "## Core Flow",
        "",
        f"- {_wiki_link('Using Gainz From Import To Audit Packet', 'Using-Gainz-From-Import-To-Audit-Packet')}",
        f"- [Download Gainz]({_site_url_for(DOCS_ROOT / 'download.md', site_url)})",
        f"- [How Gainz Calculates Basis]({_site_url_for(DOCS_ROOT / 'how-gainz-calculates-basis.md', site_url)})",
        "",
        "## Public Guides",
        "",
    ]
    lines.extend(_link_line(path, site_url) for path in guide_paths)

    lines.extend(
        [
            "",
            "## Useful Screenshots",
            "",
        ]
    )
    for title, filename, caption in SCREENSHOTS[:5]:
        lines.append(_screenshot_block(title, filename, caption, site_url).rstrip())
        lines.append("")

    lines.extend(
        [
            "## Privacy Note",
            "",
            "Public guides, screenshots, and demo outputs must use synthetic data only. Do not publish real saves, exports, source tax files, wallet balances, logs, screenshots of private records, or audit packets from personal data.",
            "",
        ]
    )
    return "\n".join(lines)


def build_docs_flow():
    site_url = _config_value("url", DEFAULT_SITE_URL)
    lines = [
        _generated_header("Docs-And-Website-Publishing.md").rstrip(),
        "# Docs And Website Publishing",
        "",
        "This page describes the public documentation flow after a product update. It exists so the website, GitHub README, docs folder, and wiki do not drift apart.",
        "",
        "## Source Of Truth",
        "",
        "Update `docs/` first. The website is built from `docs/`, and this wiki is generated from the same Markdown and screenshots.",
        "",
        "Main places to update:",
        "",
        "- `docs/user-walkthrough.md` for click-by-click workflow changes.",
        "- `docs/download.md` for launcher, packaging, and first-run changes.",
        "- `docs/how-gainz-calculates-basis.md` for basis methodology changes.",
        "- `docs/guides/*.md` for focused import, holdings, audit packet, CPA, and troubleshooting guides.",
        "- `docs/assets/screenshots/` for synthetic screenshots that are safe to publish.",
        "- `README.md` when a change affects the GitHub landing page.",
        "",
        "## Update Flow",
        "",
        "1. Make the product change.",
        "2. Capture or update synthetic screenshots when the visible workflow changed.",
        "3. Update the relevant files in `docs/`.",
        "4. Update `README.md` only when the GitHub landing page needs the same information.",
        "5. Generate the wiki pages locally.",
        "6. Run tests and whitespace checks.",
        "7. Commit and push to `main`.",
        "8. Verify the GitHub Actions checks and Netlify deploy.",
        "9. Spot-check the website and wiki links after the automation finishes.",
        "",
        "## Local Checks",
        "",
        "```powershell",
        "python .\\scripts\\generate_wiki_home.py --output-dir .\\build\\wiki",
        "python -m pytest Tests",
        "git diff --check",
        "```",
        "",
        "## Automation",
        "",
        f"- Netlify builds the public website from `docs/` and publishes it at <{site_url}>.",
        "- `.github/workflows/pages.yml` is a docs build check, not a GitHub Pages deploy.",
        "- `.github/workflows/sync-wiki.yml` regenerates the wiki pages from `docs/`, removes stale wiki-only pages, and pushes the generated wiki.",
        "- The wiki should not be manually edited for product docs. Manual edits will be overwritten by the next sync.",
        "",
        "## Privacy Rule",
        "",
        "Only publish synthetic screenshots, demo CSVs, and synthetic sample packets. Never commit or publish personal saves, source tax files, exported audit packets from real data, logs, uploaded CSVs, local plans, credentials, or screenshots that reveal private records.",
        "",
        "## Public Destinations",
        "",
        f"- Website: <{site_url}>",
        f"- Repository docs: <{REPO_URL}/tree/main/docs>",
        f"- Wiki home: <{REPO_URL}/wiki>",
        "",
    ]
    return "\n".join(lines)


def build_pages():
    return {
        "Home.md": build_home(),
        "Using-Gainz-From-Import-To-Audit-Packet.md": build_walkthrough(),
        "Guides.md": build_guides(),
        "Docs-And-Website-Publishing.md": build_docs_flow(),
    }


def write_pages(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for filename, content in build_pages().items():
        output_path = output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        written.append(output_path)
    return written


def main():
    parser = argparse.ArgumentParser(description="Generate GitHub Wiki pages from docs/.")
    parser.add_argument(
        "--output",
        default=None,
        help="Compatibility output path for only the generated wiki Home.md file.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for all generated wiki Markdown pages.",
    )
    args = parser.parse_args()

    if args.output_dir:
        paths = write_pages(Path(args.output_dir))
        for path in paths:
            print(f"Wrote {path}")
        return

    output_path = Path(args.output or REPO_ROOT / "build" / "wiki" / "Home.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_home(), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
