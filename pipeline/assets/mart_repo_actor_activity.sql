/* @bruin
name: mart_actor_repo_activity
type: duckdb.sql
materialization:
  type: table
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