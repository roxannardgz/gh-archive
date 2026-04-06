"""@bruin
name: download_gharchive_cloud
image: python:3.11
secrets:
  - key: gharchive_bq
    inject_as: GCP_CONN
@bruin"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta

from google.cloud import bigquery
from google.oauth2 import service_account


def get_bucket_name() -> str:
    return os.environ.get("GCS_BUCKET", "gharchive-491810-bucket")


def parse_date(value: str) -> date:
    if "T" in value:
        value = value.split("T")[0]
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_target_day() -> date:
    bruin_execution_date = os.environ.get("BRUIN_EXECUTION_DATE")
    if bruin_execution_date:
        return parse_date(bruin_execution_date) - timedelta(days=1)

    return date.today() - timedelta(days=1)


def build_gcs_uri_for_day(day: date) -> str:
    bucket = get_bucket_name()

    return (
        f"gs://{bucket}/"
        f"raw/year={day.year}/month={day.month:02d}/day={day.day:02d}/"
        f"part-*.parquet"
    )


def get_bigquery_client() -> bigquery.Client:
    raw = json.loads(os.environ["GCP_CONN"])

    project_id = os.environ.get("GCP_PROJECT_ID", raw["project_id"])
    service_account_json = raw.get("service_account_json")

    if service_account_json:
        sa_info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(sa_info)
        return bigquery.Client(project=project_id, credentials=credentials)

    if raw.get("use_application_default_credentials"):
        return bigquery.Client(project=project_id)

    raise ValueError(
        "GCP connection must include either a non-empty 'service_account_json' "
        "or 'use_application_default_credentials: true'."
    )


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

    client = get_bigquery_client()
    job = client.query(query, location="US")
    job.result()


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

    target_day = get_target_day()

    print(f"Cloud mode. Target day: {target_day}")
    export_day_to_gcs(target_day)

    elapsed = time.time() - start_time
    print(f"Done. Total runtime: {format_seconds(elapsed)}")

    print("BRUIN_EXECUTION_DATE =", os.environ.get("BRUIN_EXECUTION_DATE"))
    print("TARGET_DAY =", get_target_day())


if __name__ == "__main__":
    main()