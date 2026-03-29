/* @bruin
name: stg_events
type: duckdb.sql
depends:
  - raw_events
materialization:
  type: table
@bruin */

SELECT
    id AS event_id,
    "type" AS event_type,
    actor.id AS actor_id,
    actor.login AS actor_login,
    repo.id AS repo_id,
    repo.name AS repo_name,
    created_at,
    org.id AS org_id,
    org.login AS org_login,
    filename
FROM raw_events;