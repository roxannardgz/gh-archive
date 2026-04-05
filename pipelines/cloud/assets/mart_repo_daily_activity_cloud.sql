/* @bruin
name: mart_repo_daily_activity_cloud
type: bq.sql
depends:
  - stg_selected_events_cloud

custom_checks:
  - name: row count greater than zero for loaded range
    query: |
      SELECT COUNT(*) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_activity`
      WHERE event_date BETWEEN DATE('{{ start_date }}') AND DATE('{{ end_date }}')
    value: 1

  - name: valid event counts for loaded range
    query: |
      SELECT MIN(total_events) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_activity`
      WHERE event_date BETWEEN DATE('{{ start_date }}') AND DATE('{{ end_date }}')
    value: 1

  - name: valid actor counts for loaded range
    query: |
      SELECT MIN(unique_actors) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_activity`
      WHERE event_date BETWEEN DATE('{{ start_date }}') AND DATE('{{ end_date }}')
    value: 1

  - name: unique grain for loaded range
    query: |
      SELECT COUNT(*) = COUNT(DISTINCT CONCAT(repo_name, CAST(event_date AS STRING)))
      FROM `gharchive-491810.gharchive_dataset.mart_repo_daily_activity`
      WHERE event_date BETWEEN DATE('{{ start_date }}') AND DATE('{{ end_date }}')
    value: 1

@bruin */

DECLARE start_date DATE DEFAULT DATE('{{ start_date }}');
DECLARE end_date DATE DEFAULT DATE('{{ end_date }}');

CREATE TABLE IF NOT EXISTS `gharchive-491810.gharchive_dataset.mart_repo_daily_activity` (
  repo_name STRING,
  event_date DATE,
  total_events INT64,
  unique_actors INT64
)
PARTITION BY event_date
CLUSTER BY repo_name;

MERGE `gharchive-491810.gharchive_dataset.mart_repo_daily_activity` AS target
USING (
  SELECT
    repo_name,
    DATE(created_at) AS event_date,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS unique_actors
  FROM `gharchive-491810.gharchive_dataset.stg_selected_events`
  WHERE DATE(created_at) BETWEEN start_date AND end_date
  GROUP BY repo_name, DATE(created_at)
) AS source
ON target.repo_name = source.repo_name
AND target.event_date = source.event_date

WHEN MATCHED THEN UPDATE SET
  total_events = source.total_events,
  unique_actors = source.unique_actors

WHEN NOT MATCHED THEN INSERT (
  repo_name,
  event_date,
  total_events,
  unique_actors
) VALUES (
  source.repo_name,
  source.event_date,
  source.total_events,
  source.unique_actors
);