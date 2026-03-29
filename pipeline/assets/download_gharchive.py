"""@bruin
name: download_gharchive
image: python:3.11
@bruin"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import date, datetime, timedelta
from pathlib import Path


BASE_URL = "https://data.gharchive.org"
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(value: str) -> date:
    # Bruin may pass timestamps like 2025-03-15T00:00:00Z
    if "T" in value:
        value = value.split("T")[0]
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_window_end() -> date:
    """
    If Bruin provides an end date, use it as the window end date.
    Otherwise default to yesterday.
    """
    bruin_end_date = os.environ.get("BRUIN_END_DATE")
    if bruin_end_date:
        return parse_date(bruin_end_date)

    return date.today() - timedelta(days=1)


def get_window_start(window_end: date) -> date:
    return window_end - timedelta(days=6)


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def expected_filenames(start: date, end: date) -> set[str]:
    files: set[str] = set()
    for day in daterange(start, end):
        for hour in range(24):
            files.add(f"{day.isoformat()}-{hour}.json.gz")
    return files


def download_file(filename: str) -> None:
    destination = RAW_DIR / filename
    if destination.exists():
        print(f"Skipping {filename} (already exists)")
        return

    url = f"{BASE_URL}/{filename}"
    print(f"Downloading {filename}")

    try:
        subprocess.run(
            [
                "curl",
                "-fL",
                "-C", "-",
                "--retry", "5",
                "--retry-all-errors",
                "--retry-delay", "5",
                "--connect-timeout", "20",
                "--max-time", "150",
                "-o", str(destination),
                url,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        if destination.exists():
            destination.unlink()
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc


def cleanup_raw_dir(keep_files: set[str]) -> None:
    for path in RAW_DIR.glob("*.json.gz"):
        if path.name not in keep_files:
            print(f"Removing old file {path.name}")
            path.unlink()


def format_seconds(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def main() -> None:
    start_time = time.time()

    window_end = get_window_end()
    window_start = get_window_start(window_end)

    print(f"Target window: {window_start} to {window_end}")

    keep_files = expected_filenames(window_start, window_end)

    for filename in sorted(keep_files):
        download_file(filename)

    cleanup_raw_dir(keep_files)

    elapsed = time.time() - start_time
    print(
        f"Done. Raw directory now matches window {window_start} to {window_end} "
        f"({len(keep_files)} files expected). Total runtime: {format_seconds(elapsed)}"
    )


if __name__ == "__main__":
    main()