/* @bruin
name: mart_repo_daily_event_type_activity_cloud
type: bq.sql
depends:
  - stg_selected_events_cloud

checks:
  - name: repo_name
    type: not_null
  - name: event_date
    type: not_null
  - name: event_type
    type: not_null

custom_checks:
  - name: row count greater than zero for target date
    description: mart should not be empty for the loaded date
    query: |
      SELECT COUNT(*) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_event_type_activity`
      WHERE event_date = DATE('{{ end_date }}')
    value: 1

  - name: valid event counts for target date
    description: total events should be positive
    query: |
      SELECT MIN(total_events) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_event_type_activity`
      WHERE event_date = DATE('{{ end_date }}')
    value: 1

  - name: valid actor counts for target date
    description: unique actors should be positive
    query: |
      SELECT MIN(unique_actors) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_event_type_activity`
      WHERE event_date = DATE('{{ end_date }}')
    value: 1

  - name: unique grain for target date
    description: one row per repo per day per event type
    query: |
      SELECT COUNT(*) = COUNT(DISTINCT CONCAT(repo_name, CAST(event_date AS STRING), event_type))
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_event_type_activity`
      WHERE event_date = DATE('{{ end_date }}')
    value: 1

@bruin */

DECLARE target_date DATE DEFAULT DATE('{{ end_date }}');

CREATE TABLE IF NOT EXISTS `gharchive-491810.gharchive_dataset.mart_repo_daily_event_type_activity` (
  repo_name STRING,
  event_date DATE,
  event_type STRING,
  total_events INT64,
  unique_actors INT64
)
PARTITION BY event_date
CLUSTER BY repo_name, event_type;

MERGE `gharchive-491810.gharchive_dataset.mart_repo_daily_event_type_activity` AS target
USING (
  SELECT
    repo_name,
    DATE(created_at) AS event_date,
    event_type,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS unique_actors
  FROM `gharchive-491810.gharchive_dataset.stg_selected_events`
  WHERE DATE(created_at) = target_date
  GROUP BY repo_name, DATE(created_at), event_type
) AS source
ON target.repo_name = source.repo_name
AND target.event_date = source.event_date
AND target.event_type = source.event_type
AND target.event_date = target_date
WHEN MATCHED THEN UPDATE SET
  total_events = source.total_events,
  unique_actors = source.unique_actors
WHEN NOT MATCHED THEN INSERT (
  repo_name,
  event_date,
  event_type,
  total_events,
  unique_actors
) VALUES (
  source.repo_name,
  source.event_date,
  source.event_type,
  source.total_events,
  source.unique_actors
);