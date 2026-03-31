"""@bruin
name: download_gharchive
image: python:3.11
@bruin"""

from __future__ import annotations

import gzip
import os
import json
import subprocess
import time
from datetime import date, datetime, timedelta
from pathlib import Path


BASE_URL = "https://data.gharchive.org"
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

HOURS_PER_DAY = 24
MIN_BYTES = 1_000_000  # 1 MB

def get_storage_mode() -> str:
    vars_json = os.environ.get("BRUIN_VARS", "{}")
    vars_dict = json.loads(vars_json)

    value = str(vars_dict.get("storage_mode", "local")).strip().lower()

    if value not in {"local", "cloud"}:
        raise ValueError(
            f"Invalid storage_mode: {value}. Expected 'local' or 'cloud'."
        )

    return value


def get_cloud_start_date() -> date:
    vars_json = os.environ.get("BRUIN_VARS", "{}")
    vars_dict = json.loads(vars_json)

    value = vars_dict.get("cloud_start_date", "2026-03-01")
    return parse_date(str(value))


def get_lookback_days() -> int:
    vars_json = os.environ.get("BRUIN_VARS", "{}")
    vars_dict = json.loads(vars_json)

    value = vars_dict.get("lookback_days", 7)

    try:
        days = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid lookback_days value: {value}") from exc

    if days < 1:
        raise ValueError(f"lookback_days must be at least 1, got {days}")

    return days


def get_window_start_from_env() -> date | None:
    bruin_start_date = os.environ.get("BRUIN_START_DATE")
    if bruin_start_date:
        return parse_date(bruin_start_date)
    return None


def get_window_bounds(storage_mode: str) -> tuple[date, date]:
    window_end = get_window_end()

    if storage_mode == "local":
        lookback_days = get_lookback_days()
        window_start = get_window_start(window_end, lookback_days)
        return window_start, window_end

    # cloud mode
    window_start_from_env = get_window_start_from_env()

    if window_start_from_env:
        return window_start_from_env, window_end

    return window_end, window_end


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


def get_window_start(window_end: date, lookback_days: int) -> date:
    return window_end - timedelta(days=lookback_days - 1)


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def expected_filenames(start: date, end: date) -> set[str]:
    files: set[str] = set()
    for day in daterange(start, end):
        for hour in range(HOURS_PER_DAY):
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


def validate_gzip_file(path: Path) -> None:
    try:
        with gzip.open(path, "rb") as f:
            # Read a small chunk to make sure decompression works
            f.read(1024)
    except Exception as exc:
        raise RuntimeError(f"Invalid gzip file: {path.name}: {exc}") from exc


def validate_files(keep_files: set[str]) -> None:
    actual_files = sorted(RAW_DIR.glob("*.json.gz"))

    if not actual_files:
        raise RuntimeError(f"No .json.gz files found in {RAW_DIR}")

    actual_names = {path.name for path in actual_files}
    expected_count = len(keep_files)
    actual_count = len(actual_files)

    if actual_count < expected_count:
        missing_files = sorted(keep_files - actual_names)
        print(
            f"WARNING: Expected {expected_count} files but found {actual_count}. "
            f"Missing {len(missing_files)} files."
        )
        for missing in missing_files[:10]:
            print(f"WARNING: Missing file: {missing}")
        if len(missing_files) > 10:
            print(f"WARNING: ... and {len(missing_files) - 10} more missing files.")

    for path in actual_files:
        size_bytes = path.stat().st_size
        if size_bytes < MIN_BYTES:
            raise RuntimeError(
                f"File {path.name} is too small: {size_bytes} bytes "
                f"(minimum expected {MIN_BYTES})"
            )

        validate_gzip_file(path)

    print(
        f"File validation completed. Found {actual_count} files in raw directory."
    )


def format_seconds(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def run_local_mode(window_start: date, window_end: date) -> None:
    keep_files = expected_filenames(window_start, window_end)

    for filename in sorted(keep_files):
        download_file(filename)

    cleanup_raw_dir(keep_files)
    validate_files(keep_files)

def export_day_to_gcs(day: date) -> None:
    gcs_uri = build_gcs_uri_for_day(day)

    query = f"""
    EXPORT DATA OPTIONS(
        uri='{gcs_uri}',
        format='PARQUET',
        overwrite=true
    ) AS
    SELECT *
    FROM `githubarchive.day.{day.strftime("%Y%m%d")}`
    """

    print(f"Exporting {day} to {gcs_uri}")

    subprocess.run(
        ["bq", "query", "--use_legacy_sql=false", "--location=US", query],
        check=True,
    )
    
    
def run_cloud_mode(window_start: date, window_end: date) -> None:
    for day in daterange(window_start, window_end):
        export_day_to_gcs(day)


def build_gcs_uri_for_day(day: date) -> str:
    return (
        f"gs://gharchive-491810-bucket/"
        f"raw/year={day.year}/month={day.month:02d}/day={day.day:02d}/"
        f"part-*.parquet"
    )

def get_bucket_name() -> str:
    return "gharchive-491810-bucket"


def main() -> None:
    start_time = time.time()

    storage_mode = get_storage_mode()
    window_start, window_end = get_window_bounds(storage_mode)

    if storage_mode == "local":
        lookback_days = get_lookback_days()
        print(
            f"Storage mode: {storage_mode}. "
            f"Target window: {window_start} to {window_end} "
            f"({lookback_days} day(s))"
        )
    else:
        print(
            f"Storage mode: {storage_mode}. "
            f"Target window: {window_start} to {window_end}"
        )

    if storage_mode == "local":
        run_local_mode(window_start, window_end)
    else:
        run_cloud_mode(window_start, window_end)

    elapsed = time.time() - start_time
    print(f"Done. Total runtime: {format_seconds(elapsed)}")


if __name__ == "__main__":
    main()