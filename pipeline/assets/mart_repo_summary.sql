/* @bruin
name: mart_repo_summary
type: duckdb.sql
materialization:
  type: table
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