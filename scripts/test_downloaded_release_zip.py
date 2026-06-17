import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_REPO = "salexandert/Gainz"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


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
        find_member(extract_dir, "README.md")
        find_member(extract_dir, "LICENSE")

        if args.launch:
            assert_port_available(DEFAULT_HOST, DEFAULT_PORT)
            launched = True
            env = {
                **os.environ,
                "GAINZ_AUTO_OPEN": "0",
                "GAINZ_PORT": str(DEFAULT_PORT),
            }
            process = subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), env=env)
            try:
                wait_for_healthz(args.version, args.timeout)
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
