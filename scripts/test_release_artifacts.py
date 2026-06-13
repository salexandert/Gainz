import argparse
import hashlib
import sys
import zipfile
from pathlib import Path


def read_expected_hash(path):
    text = path.read_text(encoding="utf-8").strip()
    return text.split()[0].lower()


def assert_checksum(zip_path):
    checksum_path = Path(f"{zip_path}.sha256")
    if not checksum_path.exists():
        raise AssertionError(f"Missing checksum file: {checksum_path}")

    actual = hashlib.sha256(zip_path.read_bytes()).hexdigest().lower()
    expected = read_expected_hash(checksum_path)
    if actual != expected:
        raise AssertionError(
            f"Checksum mismatch for {zip_path.name}: expected {expected}, got {actual}"
        )


def assert_zip_members(zip_path, required_members):
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        for member in required_members:
            if not any(name.endswith(member) for name in names):
                raise AssertionError(f"{zip_path.name} is missing {member}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default="dist")
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--platform",
        choices=("windows", "macos"),
        required=True,
    )
    args = parser.parse_args()

    dist = Path(args.dist)
    if args.platform == "windows":
        zips = [
            dist / "Gainz-Windows.zip",
            dist / f"Gainz-Windows-v{args.version}.zip",
        ]
        required = ["Gainz.exe", "README.md", "LICENSE", "VERSION"]
    else:
        zips = [
            dist / "Gainz-macOS.zip",
            dist / f"Gainz-macOS-v{args.version}.zip",
        ]
        required = ["Gainz.app/", "README.md", "LICENSE", "VERSION"]

    for zip_path in zips:
        if not zip_path.exists():
            raise AssertionError(f"Missing release zip: {zip_path}")
        assert_checksum(zip_path)
        assert_zip_members(zip_path, required)

    print(f"{args.platform} release artifacts look valid.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"Release artifact check failed: {exc}", file=sys.stderr)
        sys.exit(1)
