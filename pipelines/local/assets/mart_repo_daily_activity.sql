/* @bruin
name: mart_repo_daily_activity
type: duckdb.sql
depends:
  - stg_selected_events
materialization:
  type: table

columns:
  - name: repo_name
    checks:
      - name: not_null
  - name: event_date
    checks:
      - name: not_null

custom_checks:
  - name: row count greater than zero
    description: mart should not be empty
    query: SELECT COUNT(*) > 0 FROM mart_repo_daily_activity
    value: 1

  - name: valid event counts
    description: total events should be positive
    query: SELECT MIN(total_events) > 0 FROM mart_repo_daily_activity
    value: 1

  - name: valid actor counts
    description: unique actors should be positive
    query: SELECT MIN(unique_actors) > 0 FROM mart_repo_daily_activity
    value: 1

  - name: unique grain
    description: one row per repo per day
    query: SELECT COUNT(*) = COUNT(DISTINCT repo_name || event_date) FROM mart_repo_daily_activity
    value: 1

@bruin */

SELECT
    repo_name,
    DATE(created_at) AS event_date,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS unique_actors
FROM stg_selected_events
GROUP BY
    repo_name,
    DATE(created_at);