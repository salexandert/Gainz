#!/usr/bin/env python3
"""
Report GitHub release downloads and optional repository traffic for Gainz.

Release asset download counts are public. Repository traffic endpoints require
a token with push access to the repository, exposed as GITHUB_TOKEN.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


DEFAULT_REPO = "salexandert/Gainz"
API_ROOT = "https://api.github.com"
DEFAULT_SNAPSHOT_DIR = "metrics/github-release-downloads"


def github_get(path, token=None):
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gainz-metrics",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {error.code} for {path}: {body}") from error


def release_downloads(repo, token=None):
    releases = github_get(f"/repos/{repo}/releases", token=token)
    rows = []
    for release in releases:
        for asset in release.get("assets", []):
            rows.append({
                "release": release.get("tag_name") or release.get("name") or "untagged",
                "asset": asset.get("name"),
                "downloads": asset.get("download_count", 0),
                "updated_at": asset.get("updated_at"),
                "url": asset.get("browser_download_url"),
            })
    return rows


def write_release_download_snapshot(rows, snapshot_dir=DEFAULT_SNAPSHOT_DIR, captured_at=None):
    """Write an idempotent daily JSON snapshot of release asset downloads."""
    if captured_at is None:
        captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    snapshot_date = captured_at[:10]
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            str(row.get("release") or ""),
            str(row.get("asset") or ""),
        ),
    )
    payload = {
        "snapshot_date": snapshot_date,
        "captured_at": captured_at,
        "total_downloads": sum(int(row.get("downloads") or 0) for row in sorted_rows),
        "release_assets": sorted_rows,
    }

    snapshot_path = Path(snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)
    daily_path = snapshot_path / f"release-downloads-{snapshot_date}.json"
    latest_path = snapshot_path / "release-downloads-latest.json"

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    daily_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")

    return {
        "daily": str(daily_path),
        "latest": str(latest_path),
        "snapshot_date": snapshot_date,
        "total_downloads": payload["total_downloads"],
    }


def repo_traffic(repo, token):
    if not token:
        return {
            "available": False,
            "reason": "Set GITHUB_TOKEN with repository push access to read traffic views, clones, referrers, and popular paths.",
        }

    paths = {
        "views": f"/repos/{repo}/traffic/views",
        "clones": f"/repos/{repo}/traffic/clones",
        "referrers": f"/repos/{repo}/traffic/popular/referrers",
        "popular_paths": f"/repos/{repo}/traffic/popular/paths",
    }
    traffic = {"available": True}
    for key, path in paths.items():
        traffic[key] = github_get(path, token=token)
    return traffic


def build_report(repo, token=None, include_traffic=True):
    return {
        "repo": repo,
        "release_assets": release_downloads(repo, token=token),
        "traffic": repo_traffic(repo, token) if include_traffic else {
            "available": False,
            "reason": "Repository traffic skipped for download-only run.",
        },
    }


def print_text_report(report):
    print(f"Repository: {report['repo']}")
    print()
    print("Release asset downloads")
    print("-----------------------")
    if not report["release_assets"]:
        print("No release assets found.")
    for row in report["release_assets"]:
        print(f"{row['release']:10} {row['downloads']:6}  {row['asset']}")

    snapshot = report.get("download_snapshot")
    if snapshot:
        print()
        print("Snapshot")
        print("--------")
        print(f"Date:  {snapshot['snapshot_date']}")
        print(f"Total: {snapshot['total_downloads']} downloads")
        print(f"Daily: {snapshot['daily']}")
        print(f"Latest: {snapshot['latest']}")

    print()
    traffic = report["traffic"]
    if not traffic.get("available"):
        print("Repository traffic")
        print("------------------")
        print(traffic["reason"])
        return

    views = traffic["views"]
    clones = traffic["clones"]
    print("Repository traffic")
    print("------------------")
    print(f"Views:  {views.get('count', 0)} total, {views.get('uniques', 0)} unique")
    print(f"Clones: {clones.get('count', 0)} total, {clones.get('uniques', 0)} unique")

    print()
    print("Top referrers")
    print("-------------")
    for referrer in traffic.get("referrers", []):
        print(f"{referrer.get('count', 0):6} total / {referrer.get('uniques', 0):4} unique  {referrer.get('referrer')}")

    print()
    print("Top GitHub paths")
    print("----------------")
    for path in traffic.get("popular_paths", []):
        print(f"{path.get('count', 0):6} total / {path.get('uniques', 0):4} unique  {path.get('path')}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report Gainz GitHub downloads and repository traffic.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Repository in owner/name format.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a text report.")
    parser.add_argument(
        "--downloads-only",
        action="store_true",
        help="Skip repository traffic endpoints and report public release asset downloads only.",
    )
    parser.add_argument(
        "--snapshot-dir",
        help=f"Write a daily release download snapshot under this directory. Default target is {DEFAULT_SNAPSHOT_DIR}.",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    report = build_report(args.repo, token=token, include_traffic=not args.downloads_only)
    if args.snapshot_dir:
        report["download_snapshot"] = write_release_download_snapshot(
            report["release_assets"],
            snapshot_dir=args.snapshot_dir,
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
