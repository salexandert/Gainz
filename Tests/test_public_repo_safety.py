import subprocess
import sys
from pathlib import Path


PRIVATE_PATH_PARTS = {
    "saves",
    "exports",
    "logs",
    "audit_packets",
    "instance",
    "uploads",
    "quarantine",
    "reconciliation",
    "local_plans",
    "CSVs",
    "App Test Data",
}

SENSITIVE_TEXT_MARKERS = (
    "C:\\Users\\",
    "OneDrive\\Taxes",
    "saved_Y",
    "Coinbase_All_Transactions",
    "transactions_2025.csv",
)

PUBLIC_CSV_PREFIXES = (
    "demo_data/",
    "Tests/fixtures/",
)


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_private_runtime_paths_are_not_tracked():
    offenders = []
    for path in tracked_files():
        parts = Path(path).parts
        if any(part in PRIVATE_PATH_PARTS for part in parts):
            offenders.append(path)

    assert offenders == []


def test_only_public_synthetic_csvs_are_tracked():
    offenders = [
        path
        for path in tracked_files()
        if path.lower().endswith(".csv")
        and not path.startswith(PUBLIC_CSV_PREFIXES)
    ]

    assert offenders == []


def test_public_text_files_do_not_reference_private_local_data():
    searchable_suffixes = {
        ".cfg",
        ".csv",
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".py",
        ".toml",
        ".txt",
        ".xml",
        ".yml",
        ".yaml",
    }
    offenders = []

    for path in tracked_files():
        if path == "Tests/test_public_repo_safety.py":
            continue
        file_path = Path(path)
        if not file_path.exists():
            continue
        if file_path.suffix.lower() not in searchable_suffixes:
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for marker in SENSITIVE_TEXT_MARKERS:
            if marker in text:
                offenders.append(f"{path}: {marker}")

    assert offenders == []


def test_generated_wiki_pages_use_public_docs(tmp_path):
    output_dir = tmp_path / "wiki"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_wiki_home.py",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_pages = {
        "Home.md",
        "Using-Gainz-From-Import-To-Audit-Packet.md",
        "Guides.md",
        "Docs-And-Website-Publishing.md",
    }
    generated_pages = {path.name for path in output_dir.glob("*.md")}
    assert generated_pages == expected_pages

    combined_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(output_dir.glob("*.md"))
    )
    assert "[Download Gainz](https://cryptogainz.store/download/)" in combined_text
    assert "https://cryptogainz.store/user-walkthrough/" in combined_text
    assert (
        "https://raw.githubusercontent.com/salexandert/Gainz/main/docs/assets/screenshots/gainz-manual-batch-entry.png"
        in combined_text
    )
    assert "https://cryptogainz.store/assets/screenshots/" not in combined_text
    assert "Using Gainz From Import To Audit Packet" in combined_text
    assert "Crypto Tax Reconciliation Guides" in combined_text
    assert "generated from docs/" in combined_text
    assert "gainz-home.png" in combined_text
    assert "Docs And Website Publishing" in combined_text
    assert "relative_url" not in combined_text
    assert "{{" not in combined_text
    assert "Step-1:-Import-CSV" not in combined_text

    for marker in SENSITIVE_TEXT_MARKERS:
        assert marker not in combined_text

    assert "C:\\" not in combined_text
    assert "OneDrive" not in combined_text
