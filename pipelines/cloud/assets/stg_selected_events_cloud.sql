/* @bruin
name: stg_selected_events_cloud
type: bq.sql
depends:
  - stg_events_cloud

custom_checks:
  - name: row count greater than zero for loaded range
    description: stg_selected_events_cloud should not be empty for the loaded range
    query: |
      SELECT COUNT(*) > 0
      FROM `gharchive-491810.gharchive_dataset.stg_selected_events`
      WHERE DATE(created_at) BETWEEN DATE('{{ start_date }}') AND DATE('{{ end_date }}')
    value: 1

@bruin */

DECLARE start_date DATE DEFAULT DATE('{{ start_date }}');
DECLARE end_date DATE DEFAULT DATE('{{ end_date }}');

CREATE TABLE IF NOT EXISTS `gharchive-491810.gharchive_dataset.stg_selected_events` (
  event_id STRING,
  event_type STRING,
  actor_id INT64,
  actor_login STRING,
  repo_id INT64,
  repo_name STRING,
  created_at TIMESTAMP,
  org_id INT64,
  org_login STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY repo_name;

DELETE FROM `gharchive-491810.gharchive_dataset.stg_selected_events`
WHERE DATE(created_at) BETWEEN start_date AND end_date;

INSERT INTO `gharchive-491810.gharchive_dataset.stg_selected_events`
SELECT *
FROM `gharchive-491810.gharchive_dataset.stg_events`
WHERE DATE(created_at) BETWEEN start_date AND end_date
  AND repo_name IN (
    'apache/airflow',
    'ClickHouse/ClickHouse',
    'metabase/metabase',
    'apache/superset',
    'airbytehq/airbyte',
    'apache/spark',
    'trinodb/trino',
    'duckdb/duckdb',
    'dbt-labs/dbt-core',
    'dagster-io/dagster',
    'PrefectHQ/prefect',
    'apache/flink',
    'DataTalksClub/data-engineering-zoomcamp',
    'kestra-io/kestra',
    'bruin-data/bruin'
  );