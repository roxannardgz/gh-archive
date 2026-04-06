"""@bruin
name: download_gharchive_cloud
image: python:3.11
@bruin"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import date, datetime, timedelta
from google.cloud import bigquery


def parse_date(value: str) -> date:
    if "T" in value:
        value = value.split("T")[0]
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_window_end() -> date:
    bruin_end_date = os.environ.get("BRUIN_END_DATE")
    if bruin_end_date:
        return parse_date(bruin_end_date)

    return date.today() - timedelta(days=1)


def get_window_start_from_env() -> date | None:
    bruin_start_date = os.environ.get("BRUIN_START_DATE")
    if bruin_start_date:
        return parse_date(bruin_start_date)
    return None


def get_window_bounds() -> tuple[date, date]:
    window_end = get_window_end()
    window_start_from_env = get_window_start_from_env()

    if window_start_from_env:
        return window_start_from_env, window_end

    return window_end, window_end


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_gcs_uri_for_day(day: date) -> str:
    return (
        f"gs://gharchive-491810-bucket/"
        f"raw/year={day.year}/month={day.month:02d}/day={day.day:02d}/"
        f"part-*.parquet"
    )


# def export_day_to_gcs(day: date) -> None:
#     gcs_uri = build_gcs_uri_for_day(day)
# 
#     query = f"""
#     EXPORT DATA OPTIONS(
#         uri='{gcs_uri}',
#         format='PARQUET',
#         overwrite=true
#     ) AS
#     SELECT *
#     FROM `githubarchive.day.{day.strftime("%Y%m%d")}`
#     """
# 
#     print(f"Exporting {day} to {gcs_uri}")
# 
#     subprocess.run(
#         ["bq", "query", "--use_legacy_sql=false", "--location=US", query],
#         check=True,
#     )


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

    client = bigquery.Client(project="gharchive-491810")
    job = client.query(query, location="US")
    job.result()


def run_cloud_mode(window_start: date, window_end: date) -> None:
    for day in daterange(window_start, window_end):
        export_day_to_gcs(day)


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

    window_start, window_end = get_window_bounds()

    print(f"Cloud mode. Target window: {window_start} to {window_end}")

    run_cloud_mode(window_start, window_end)

    elapsed = time.time() - start_time
    print(f"Done. Total runtime: {format_seconds(elapsed)}")


if __name__ == "__main__":
    main()