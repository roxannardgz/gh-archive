/* @bruin
name: stg_events_cloud
type: bq.sql
depends:
  - raw_events_cloud

checks:
  - name: event_id
    type: not_null
  - name: event_type
    type: not_null
  - name: repo_name
    type: not_null
  - name: created_at
    type: not_null

custom_checks:
  - name: no duplicate event ids for target date
    description: stg_events_cloud should have unique event ids within the loaded date
    query: |
      SELECT COUNT(*) = COUNT(DISTINCT event_id)
      FROM `gharchive-491810.gharchive_dataset.stg_events`
      WHERE DATE(created_at) BETWEEN DATE('{{ start_date }}') AND DATE('{{ end_date }}')
    value: 1

@bruin */

DECLARE start_date DATE DEFAULT DATE('{{ start_date }}');
DECLARE end_date DATE DEFAULT DATE('{{ end_date }}');

CREATE TABLE IF NOT EXISTS `gharchive-491810.gharchive_dataset.stg_events` (
  event_id STRING,
  event_type STRING,
  actor_id INT64,
  actor_login STRING,
  repo_id INT64,
  repo_name STRING,
  created_at TIMESTAMP,
  org_id INT64,
  org_login STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY repo_name;

DELETE FROM `gharchive-491810.gharchive_dataset.stg_events`
WHERE DATE(created_at) BETWEEN start_date AND end_date;

INSERT INTO `gharchive-491810.gharchive_dataset.stg_events`
WITH deduplicated AS (
    SELECT
        id,
        type,
        actor,
        repo,
        created_at,
        org,
        ROW_NUMBER() OVER (
            PARTITION BY id
            ORDER BY created_at DESC
        ) AS rn
    FROM `gharchive-491810.gharchive_dataset.raw_events`
    WHERE DATE(created_at) BETWEEN start_date AND end_date
)

SELECT
    id AS event_id,
    type AS event_type,
    actor.id AS actor_id,
    actor.login AS actor_login,
    repo.id AS repo_id,
    repo.name AS repo_name,
    created_at,
    org.id AS org_id,
    org.login AS org_login
FROM deduplicated
WHERE rn = 1;