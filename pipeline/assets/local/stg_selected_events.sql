/* @bruin
name: stg_selected_events
type: duckdb.sql
depends:
  - stg_events
materialization:
  type: table

checks:
  - name: event_id
    type: not_null
  - name: repo_name
    type: not_null
  - name: created_at
    type: not_null

custom_checks:
  - name: row count greater than zero
    description: stg_selected_events should not be empty
    query: SELECT COUNT(*) > 0 FROM stg_selected_events
    value: 1
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