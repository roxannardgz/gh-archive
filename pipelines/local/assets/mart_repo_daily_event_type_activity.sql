/* @bruin
name: mart_repo_daily_event_type_activity
type: duckdb.sql
depends:
  - stg_selected_events
materialization:
  type: table

checks:
  - name: repo_name
    type: not_null
  - name: event_date
    type: not_null
  - name: event_type
    type: not_null

custom_checks:
  - name: row count greater than zero
    description: mart should not be empty
    query: SELECT COUNT(*) > 0 FROM mart_repo_daily_event_type_activity
    value: 1

  - name: valid event counts
    description: total events should be positive
    query: SELECT MIN(total_events) > 0 FROM mart_repo_daily_event_type_activity
    value: 1

  - name: valid actor counts
    description: unique actors should be positive
    query: SELECT MIN(unique_actors) > 0 FROM mart_repo_daily_event_type_activity
    value: 1

  - name: unique grain
    description: one row per repo per day per event type
    query: SELECT COUNT(*) = COUNT(DISTINCT repo_name || event_date || event_type) FROM mart_repo_daily_event_type_activity
    value: 1

@bruin */

SELECT
    repo_name,
    DATE(created_at) AS event_date,
    event_type,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS unique_actors
FROM stg_selected_events
GROUP BY
    repo_name,
    DATE(created_at),
    event_type;