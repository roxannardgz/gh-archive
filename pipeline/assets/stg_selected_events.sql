/* @bruin
name: stg_selected_events
type: duckdb.sql
materialization:
  type: table
@bruin */

SELECT *
FROM stg_events
WHERE repo_name IN (
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