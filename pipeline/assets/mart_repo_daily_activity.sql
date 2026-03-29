/* @bruin
name: mart_repo_daily_activity
type: duckdb.sql
depends:
  - stg_selected_events
materialization:
  type: table
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