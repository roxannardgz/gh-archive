/* @bruin
name: mart_repo_daily_event_type_activity
type: duckdb.sql
materialization:
  type: table
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