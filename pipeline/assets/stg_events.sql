/* @bruin
name: stg_events
type: duckdb.sql
depends:
  - raw_events
materialization:
  type: table

custom_checks:
  - name: no duplicate event ids
    description: stg_events should have unique event ids after deduplication
    query: SELECT COUNT(*) = COUNT(DISTINCT event_id) FROM stg_events
    value: 1

@bruin */

WITH deduplicated AS (
    SELECT
        id,
        "type",
        actor,
        repo,
        created_at,
        org,
        filename,
        ROW_NUMBER() OVER (
            PARTITION BY id
            ORDER BY created_at DESC, filename DESC
        ) AS rn
    FROM raw_events
)

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
FROM deduplicated
WHERE rn = 1;