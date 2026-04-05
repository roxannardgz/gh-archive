/* @bruin
name: mart_repo_summary
type: duckdb.sql
depends:
  - stg_selected_events
materialization:
  type: table

columns:
  - name: repo_name
    checks:
      - name: not_null

custom_checks:
  - name: row count greater than zero
    description: mart should not be empty
    query: SELECT COUNT(*) > 0 FROM mart_repo_summary
    value: 1

  - name: valid event counts
    description: total events should be positive
    query: SELECT MIN(total_events) > 0 FROM mart_repo_summary
    value: 1

  - name: valid actor counts
    description: unique actors should be positive
    query: SELECT MIN(unique_actors) > 0 FROM mart_repo_summary
    value: 1

  - name: valid active days
    description: active days should be positive
    query: SELECT MIN(active_days) > 0 FROM mart_repo_summary
    value: 1

  - name: valid activity range
    description: first activity should not be after last activity
    query: SELECT COUNT(*) = COUNT(CASE WHEN first_activity <= last_activity THEN 1 END)
           FROM mart_repo_summary
    value: 1

  - name: unique grain
    description: one row per repo
    query: SELECT COUNT(*) = COUNT(DISTINCT repo_name)
           FROM mart_repo_summary
    value: 1

@bruin */

SELECT
    repo_name,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS unique_actors,
    COUNT(DISTINCT DATE(created_at)) AS active_days,
    MIN(created_at) AS first_activity,
    MAX(created_at) AS last_activity
FROM stg_selected_events
GROUP BY repo_name;