/* @bruin
name: mart_repo_actor_activity
type: duckdb.sql
depends:
  - stg_selected_events
materialization:
  type: table

columns:
  - name: repo_name
    checks:
      - name: not_null
  - name: actor_login
    checks:
      - name: not_null

custom_checks:
  - name: row count greater than zero
    description: mart should not be empty
    query: SELECT COUNT(*) > 0 FROM mart_repo_actor_activity
    value: 1

  - name: valid event counts
    description: total events should be positive
    query: SELECT MIN(total_events) > 0 FROM mart_repo_actor_activity
    value: 1

  - name: valid activity range
    description: first activity should not be after last activity
    query: SELECT COUNT(*) = COUNT(CASE WHEN first_activity <= last_activity THEN 1 END)
           FROM mart_repo_actor_activity
    value: 1

  - name: unique grain
    description: one row per repo per actor
    query: SELECT COUNT(*) = COUNT(DISTINCT repo_name || actor_login)
           FROM mart_repo_actor_activity
    value: 1

@bruin */

SELECT
    repo_name,
    actor_login,
    COUNT(*) AS total_events,
    COUNT(DISTINCT event_type) AS event_types_count,
    MIN(created_at) AS first_activity,
    MAX(created_at) AS last_activity
FROM stg_selected_events
GROUP BY
    repo_name,
    actor_login;