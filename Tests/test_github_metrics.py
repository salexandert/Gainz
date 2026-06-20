import json

from scripts.github_metrics import write_release_download_snapshot


def test_release_download_snapshot_writes_daily_and_latest_json(tmp_path):
    rows = [
        {
            "release": "v0.2.16",
            "asset": "Gainz-Windows.zip",
            "downloads": 12,
            "updated_at": "2026-06-20T12:00:00Z",
            "url": "https://github.com/salexandert/Gainz/releases/download/v0.2.16/Gainz-Windows.zip",
        },
        {
            "release": "v0.2.16",
            "asset": "Gainz-macOS.zip",
            "downloads": 3,
            "updated_at": "2026-06-20T12:00:00Z",
            "url": "https://github.com/salexandert/Gainz/releases/download/v0.2.16/Gainz-macOS.zip",
        },
    ]

    result = write_release_download_snapshot(
        rows,
        snapshot_dir=tmp_path,
        captured_at="2026-06-20T13:17:00Z",
    )

    assert result["snapshot_date"] == "2026-06-20"
    assert result["total_downloads"] == 15

    daily = tmp_path / "release-downloads-2026-06-20.json"
    latest = tmp_path / "release-downloads-latest.json"
    assert daily.exists()
    assert latest.exists()

    daily_payload = json.loads(daily.read_text(encoding="utf-8"))
    latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    assert daily_payload == latest_payload
    assert daily_payload["captured_at"] == "2026-06-20T13:17:00Z"
    assert daily_payload["release_assets"][0]["asset"] == "Gainz-Windows.zip"


def test_release_download_snapshot_replaces_same_day_file(tmp_path):
    write_release_download_snapshot(
        [{"release": "v0.2.15", "asset": "old.zip", "downloads": 1}],
        snapshot_dir=tmp_path,
        captured_at="2026-06-20T01:00:00Z",
    )

    write_release_download_snapshot(
        [{"release": "v0.2.16", "asset": "new.zip", "downloads": 4}],
        snapshot_dir=tmp_path,
        captured_at="2026-06-20T13:17:00Z",
    )

    payload = json.loads((tmp_path / "release-downloads-2026-06-20.json").read_text(encoding="utf-8"))
    assert payload["total_downloads"] == 4
    assert payload["release_assets"] == [
        {"asset": "new.zip", "downloads": 4, "release": "v0.2.16"}
    ]
