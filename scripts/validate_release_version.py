import argparse
import re
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$")


def read_app_version():
    text = Path("app_version.py").read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
    if not match:
        raise ValueError("Could not find APP_VERSION in app_version.py.")
    return match.group(1)


def read_docs_version():
    text = Path("docs/_config.yml").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(.+)$", text, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in docs/_config.yml.")
    return match.group(1).strip().strip('"').strip("'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-tag", default="")
    args = parser.parse_args()

    version = Path("VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_PATTERN.match(version):
        raise ValueError(f"VERSION must be semantic version format, got '{version}'.")

    app_version = read_app_version()
    if app_version != version:
        raise ValueError(f"app_version.py ({app_version}) does not match VERSION ({version}).")

    docs_version = read_docs_version()
    if docs_version != version:
        raise ValueError(f"docs/_config.yml ({docs_version}) does not match VERSION ({version}).")

    tag = f"v{version}"
    if args.expected_tag and args.expected_tag != tag:
        raise ValueError(f"Tag {args.expected_tag} does not match VERSION {version}. Expected {tag}.")

    with open(Path(sys.argv[0]).parent / "release_version.env", "w", encoding="utf-8") as handle:
        handle.write(f"version={version}\n")
        handle.write(f"tag={tag}\n")

    print(f"version={version}")
    print(f"tag={tag}")


if __name__ == "__main__":
    main()
