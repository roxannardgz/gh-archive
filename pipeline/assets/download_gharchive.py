"""@bruin
name: download_gharchive
image: python:3.11
@bruin"""

from __future__ import annotations

import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path


BASE_URL = "https://data.gharchive.org"
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


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
                "--max-time", "300",
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


def main() -> None:
    start_date = parse_date(os.environ["BRUIN_START_DATE"])
    end_date = parse_date(os.environ["BRUIN_END_DATE"])

    keep_files = expected_filenames(start_date, end_date)

    for filename in sorted(keep_files):
        download_file(filename)

    cleanup_raw_dir(keep_files)

    print(
        f"Done. Raw directory now matches window {start_date} to {end_date} "
        f"({len(keep_files)} files expected)."
    )


if __name__ == "__main__":
    main()