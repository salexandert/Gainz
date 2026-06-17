import argparse
import csv
import http.cookiejar
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_REPO = "salexandert/Gainz"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
SMOKE_USERNAME = "release_qa_admin"
SMOKE_PASSWORD = "release-qa-password"


def download(url, destination):
    with urllib.request.urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def checksum_value(path):
    return path.read_text(encoding="utf-8").strip().split()[0].lower()


def assert_port_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        if sock.connect_ex((host, port)) == 0:
            raise AssertionError(
                f"{host}:{port} is already in use. Stop Gainz before running launch smoke."
            )


def stop_gainz_processes_from_dir(root_dir):
    if os.name != "nt":
        return

    script = r"""
$root = [System.IO.Path]::GetFullPath($env:GAINZ_RELEASE_QA_ROOT)
Get-Process -Name Gainz -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Path -and
        ([System.IO.Path]::GetFullPath($_.Path)).StartsWith(
            $root,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    } |
    Stop-Process -Force
"""
    env = {**os.environ, "GAINZ_RELEASE_QA_ROOT": str(Path(root_dir))}
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def wait_for_healthz(expected_version, timeout):
    health_url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/healthz"
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") != "ok":
                raise AssertionError(f"Unexpected health payload: {payload}")
            if payload.get("version") != expected_version:
                raise AssertionError(
                    f"Running app version {payload.get('version')} does not match {expected_version}"
                )
            return payload
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)

    raise AssertionError(f"Timed out waiting for {health_url}: {last_error}")


def read_json_response(response):
    return json.loads(response.read().decode("utf-8"))


def post_form(opener, url, data):
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return opener.open(request, timeout=60)


def post_json(opener, url, data):
    encoded = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return opener.open(request, timeout=120)


def assert_post_json_status(opener, url, data, expected_status):
    try:
        response = post_json(opener, url, data)
        status = response.status
        payload = read_json_response(response)
    except urllib.error.HTTPError as exc:
        status = exc.code
        payload = read_json_response(exc)

    if status != expected_status:
        raise AssertionError(f"{url} returned {status}; expected {expected_status}: {payload}")
    return payload


def release_smoke_base_url():
    return f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"


def build_authenticated_opener():
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    base_url = release_smoke_base_url()
    post_form(
        opener,
        f"{base_url}/login",
        {
            "username": SMOKE_USERNAME,
            "password": SMOKE_PASSWORD,
            "login": "1",
        },
    )
    return opener


def count_manifest_rows(packet_path):
    manifest_path = Path(packet_path) / "03_manifests" / "evidence_manifest.csv"
    with open(manifest_path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    return {
        "copied_sources": len([
            row for row in rows
            if row["category"] == "source_file" and row["status"] == "COPIED"
        ]),
        "copied_tax_evidence": len([
            row for row in rows
            if row["category"] == "tax_evidence" and row["status"] == "COPIED"
        ]),
        "reference_only_tax_evidence": len([
            row for row in rows
            if row["category"] == "tax_evidence" and row["status"] in {"REFERENCE", "REFERENCE_ONLY"}
        ]),
        "missing_tax_evidence": len([
            row for row in rows
            if row["category"] == "tax_evidence" and row["status"] == "MISSING"
        ]),
    }


def run_packaged_workflow_smoke(temp_path, expected_version):
    base_url = release_smoke_base_url()
    opener = build_authenticated_opener()

    read_json_response(post_form(opener, f"{base_url}/import_transactions/demo", {}))

    evidence_dir = temp_path / "synthetic-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "2024_crypto_workbook.csv"
    evidence_path.write_text(
        "Year,Reported Proceeds,Reported Cost Basis,Reported Gain Loss,Tax Paid\n"
        "2024,300.00,100.00,200.00,25.00\n",
        encoding="utf-8",
    )
    post_form(
        opener,
        f"{base_url}/tax_filing_review/evidence",
        {
            "evidence_year": "2024",
            "evidence_reference": str(evidence_path),
            "evidence_type": "crypto_workbook",
            "evidence_notes": "Synthetic release QA evidence.",
        },
    )

    output_dir = temp_path / "qa-output"
    preview_response = post_json(
        opener,
        f"{base_url}/export/packet_preview.json",
        {"output_dir": str(output_dir)},
    )
    preview_payload = read_json_response(preview_response)
    preview = preview_payload["packet_preview"]

    if preview["output_folder"] != str(output_dir.resolve()):
        raise AssertionError("Packet preview output folder did not match requested folder.")
    if not preview["is_draft"]:
        raise AssertionError("Release QA expected a draft packet for unresolved demo workflow.")
    if preview["reference_only_files_count"] < 1:
        raise AssertionError("Reference-only evidence count should include the synthetic evidence record.")

    assert_post_json_status(
        opener,
        f"{base_url}/export/save",
        {"output_dir": str(output_dir)},
        400,
    )
    assert_post_json_status(
        opener,
        f"{base_url}/export/audit_packet",
        {"output_dir": str(output_dir)},
        400,
    )
    packet_payload = assert_post_json_status(
        opener,
        f"{base_url}/export/audit_packet",
        {"output_dir": str(output_dir), "draft_acknowledged": True},
        200,
    )

    packet_path = Path(packet_payload["path"])
    if packet_path.parent != output_dir.resolve():
        raise AssertionError("Generated packet folder did not match requested output folder.")
    packet_prefix = preview["packet_name"].split("YYYY")[0]
    if not packet_path.name.startswith(packet_prefix):
        raise AssertionError(f"Packet name {packet_path.name} did not match preview prefix {packet_prefix}.")

    manifest_counts = count_manifest_rows(packet_path)
    copied_files_count = manifest_counts["copied_sources"] + manifest_counts["copied_tax_evidence"]
    if copied_files_count != preview["copied_files_count"]:
        raise AssertionError("Copied file count did not match packet preview.")
    if manifest_counts["reference_only_tax_evidence"] != preview["reference_only_files_count"]:
        raise AssertionError("Reference-only evidence count did not match packet preview.")
    if manifest_counts["missing_tax_evidence"] != preview["missing_tax_evidence_count"]:
        raise AssertionError("Missing evidence count did not match packet preview.")

    summary_path = packet_path / "03_manifests" / "audit_packet_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary["readiness_is_ready"] == preview["is_draft"]:
        raise AssertionError("Draft/readiness status mismatch between preview and packet summary.")
    if len(summary.get("readiness_blocker_groups", [])) != preview["unresolved_blocker_group_count"]:
        raise AssertionError("Blocker group count did not match packet preview.")
    if summary["tax_evidence_packet_counts"]["reference_only"] != preview["reference_only_files_count"]:
        raise AssertionError("Summary reference-only count did not match packet preview.")
    if summary["tax_evidence_packet_counts"]["missing"] != preview["missing_tax_evidence_count"]:
        raise AssertionError("Summary missing evidence count did not match packet preview.")

    health_payload = wait_for_healthz(expected_version, timeout=5)
    if health_payload.get("version") != expected_version:
        raise AssertionError("Packaged workflow smoke finished against the wrong app version.")


def release_asset_url(repo, asset, tag=None):
    if tag:
        return f"https://github.com/{repo}/releases/download/{tag}/{asset}"
    return f"https://github.com/{repo}/releases/latest/download/{asset}"


def find_member(extract_dir, member_name):
    matches = [path for path in extract_dir.rglob(member_name)]
    if not matches:
        raise AssertionError(f"Release zip is missing {member_name}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(
        description="Download and verify the public Gainz Windows release ZIP."
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--version", required=True)
    parser.add_argument("--asset", default="Gainz-Windows.zip")
    parser.add_argument("--tag", help="Download from a specific release tag instead of latest.")
    parser.add_argument("--launch", action="store_true", help="Launch Gainz.exe and verify /healthz.")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    temp_dir = tempfile.mkdtemp(prefix="gainz-release-qa-")
    launched = False
    try:
        temp_path = Path(temp_dir)
        zip_path = temp_path / args.asset
        checksum_path = temp_path / f"{args.asset}.sha256"

        download(release_asset_url(args.repo, args.asset, args.tag), zip_path)
        download(release_asset_url(args.repo, f"{args.asset}.sha256", args.tag), checksum_path)

        expected_hash = checksum_value(checksum_path)
        actual_hash = sha256(zip_path)
        if actual_hash != expected_hash:
            raise AssertionError(
                f"Checksum mismatch for {args.asset}: expected {expected_hash}, got {actual_hash}"
            )

        extract_dir = temp_path / "extracted"
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        version_path = find_member(extract_dir, "VERSION")
        packaged_version = version_path.read_text(encoding="utf-8").strip()
        if packaged_version != args.version:
            raise AssertionError(
                f"Packaged VERSION is {packaged_version}; expected {args.version}"
            )

        exe_path = find_member(extract_dir, "Gainz.exe")
        readme_path = find_member(extract_dir, "README.md")
        if args.version not in readme_path.read_text(encoding="utf-8", errors="replace"):
            raise AssertionError(f"Packaged README.md does not mention {args.version}")
        find_member(extract_dir, "LICENSE")

        if args.launch:
            assert_port_available(DEFAULT_HOST, DEFAULT_PORT)
            launched = True
            env = {
                **os.environ,
                "GAINZ_AUTO_OPEN": "0",
                "GAINZ_PORT": str(DEFAULT_PORT),
                "GAINZ_ADMIN_USERNAME": SMOKE_USERNAME,
                "GAINZ_ADMIN_PASSWORD": SMOKE_PASSWORD,
                "GAINZ_DATA_DIR": str(temp_path / "data"),
                "GAINZ_INSTANCE_PATH": str(temp_path / "instance"),
                "GAINZ_UPLOAD_FOLDER": str(temp_path / "uploads"),
                "GAINZ_EXPORT_FOLDER": str(temp_path / "exports"),
                "GAINZ_AUDIT_PACKET_FOLDER": str(temp_path / "audit_packets"),
                "GAINZ_SECRET_KEY": "release-qa-secret",
            }
            process = subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), env=env)
            try:
                wait_for_healthz(args.version, args.timeout)
                run_packaged_workflow_smoke(temp_path, args.version)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()

        print(f"{args.asset} release ZIP verified for Gainz {args.version}.")
    finally:
        if launched:
            stop_gainz_processes_from_dir(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Downloaded release ZIP check failed: {exc}", file=sys.stderr)
        sys.exit(1)
