import subprocess
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


def test_only_demo_csvs_are_tracked():
    offenders = [
        path
        for path in tracked_files()
        if path.lower().endswith(".csv") and not path.startswith("demo_data/")
    ]

    assert offenders == []


def test_public_text_files_do_not_reference_private_local_data():
    searchable_suffixes = {
        ".cfg",
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
        if file_path.suffix.lower() not in searchable_suffixes:
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for marker in SENSITIVE_TEXT_MARKERS:
            if marker in text:
                offenders.append(f"{path}: {marker}")

    assert offenders == []
