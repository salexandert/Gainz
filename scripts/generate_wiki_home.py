import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
DEFAULT_SITE_URL = "https://cryptogainz.store"

ROOT_DOCS = [
    "download.md",
    "user-walkthrough.md",
    "how-gainz-calculates-basis.md",
    "donations.md",
]


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


def _link_line(path, site_url):
    title = _title_from_path(path)
    return f"- [{title}]({_site_url_for(path, site_url)})"


def _guide_paths():
    return sorted(
        (DOCS_ROOT / "guides").glob("*.md"),
        key=lambda path: _title_from_path(path).lower(),
    )


def build_home():
    site_url = _config_value("url", DEFAULT_SITE_URL)
    version = _config_value("version", "")
    root_paths = [DOCS_ROOT / name for name in ROOT_DOCS if (DOCS_ROOT / name).exists()]
    guide_paths = _guide_paths()

    lines = [
        "<!-- This page is generated from docs/ by scripts/generate_wiki_home.py. -->",
        "<!-- Update docs/ in the main repository; do not hand-edit this generated wiki page. -->",
        "",
        "# Gainz Wiki",
        "",
        "Gainz documentation is maintained in the main repository under `docs/` and published to the public website.",
        "This wiki is a generated hub so the website, repo docs, and wiki do not drift apart.",
        "",
        f"- Public website and docs: <{site_url}>",
        "- Main repository: <https://github.com/salexandert/Gainz>",
    ]
    if version:
        lines.append(f"- Current documented version: `{version}`")

    lines.extend([
        "",
        "## Start Here",
        "",
    ])
    lines.extend(_link_line(path, site_url) for path in root_paths)

    lines.extend([
        "",
        "## Guides",
        "",
    ])
    lines.extend(_link_line(path, site_url) for path in guide_paths)

    lines.extend([
        "",
        "## Screenshots",
        "",
        "The walkthrough and website screenshots use synthetic demo data only. Public screenshots live in `docs/assets/screenshots/` in the main repository.",
        "",
        "## Important",
        "",
        "Gainz is documentation support for crypto tax review. It is not tax, legal, financial, accounting, or filing advice. Review outputs with a qualified tax professional before filing.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate the GitHub Wiki home page from docs/.")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "build" / "wiki" / "Home.md"),
        help="Output path for the generated wiki Home.md file.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_home(), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
