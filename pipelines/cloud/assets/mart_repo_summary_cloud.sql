/* @bruin
name: mart_repo_summary_cloud
type: bq.sql
depends:
  - stg_selected_events_cloud

columns:
  - name: repo_name
    checks:
      - name: not_null 

custom_checks:
  - name: row count greater than zero
    query: |
      SELECT COUNT(*) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_summary`
    value: 1

  - name: unique grain
    query: |
      SELECT COUNT(*) = COUNT(DISTINCT repo_name)
      FROM `gharchive-491810.gharchive_dataset.mart_repo_summary`
    value: 1

@bruin */

CREATE OR REPLACE TABLE `gharchive-491810.gharchive_dataset.mart_repo_summary` AS
SELECT
    repo_name,
    COUNT(*) AS total_events,
    COUNT(DISTINCT actor_login) AS total_actors,
    COUNT(DISTINCT event_type) AS total_event_types,
    MIN(created_at) AS first_activity,
    MAX(created_at) AS last_activity
FROM `gharchive-491810.gharchive_dataset.stg_selected_events`
GROUP BY repo_name;