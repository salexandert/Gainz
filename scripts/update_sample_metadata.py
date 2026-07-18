import argparse
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS_DIR = REPO_ROOT / "docs" / "assets" / "downloads"
METADATA_PATH = DOWNLOADS_DIR / "gainz-synthetic-audit-packet-sample.json"
SAMPLE_ZIP_PATH = DOWNLOADS_DIR / "gainz-synthetic-audit-packet-sample.zip"


def update_sample_metadata(version):
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    metadata["version"] = version
    metadata["sha256"] = hashlib.sha256(SAMPLE_ZIP_PATH.read_bytes()).hexdigest()
    with METADATA_PATH.open("w", encoding="utf-8", newline="\n") as metadata_file:
        metadata_file.write(json.dumps(metadata, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    update_sample_metadata(args.version)


if __name__ == "__main__":
    main()
