/* @bruin
name: mart_repo_actor_activity_cloud
type: bq.sql
depends:
  - stg_selected_events_cloud

columns:
  - name: repo_name
    checks:
      - name: not_null
  - name: actor_login
    checks:
      - name: not_null

custom_checks:
  - name: row count greater than zero
    query: |
      SELECT COUNT(*) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_actor_activity`
    value: 1

  - name: valid event counts
    query: |
      SELECT MIN(total_events) > 0
      FROM `gharchive-491810.gharchive_dataset.mart_repo_actor_activity`
    value: 1

  - name: valid activity range
    query: |
      SELECT COUNT(*) = COUNT(CASE WHEN first_activity <= last_activity THEN 1 END)
      FROM `gharchive-491810.gharchive_dataset.mart_repo_actor_activity`
    value: 1

  - name: unique grain
    query: |
      SELECT COUNT(*) = COUNT(DISTINCT CONCAT(repo_name, actor_login))
      FROM `gharchive-491810.gharchive_dataset.mart_repo_actor_activity`
    value: 1

@bruin */

CREATE OR REPLACE TABLE `gharchive-491810.gharchive_dataset.mart_repo_actor_activity` AS

SELECT
    repo_name,
    actor_login,
    COUNT(*) AS total_events,
    COUNT(DISTINCT event_type) AS event_types_count,
    MIN(created_at) AS first_activity,
    MAX(created_at) AS last_activity
FROM `gharchive-491810.gharchive_dataset.stg_selected_events`
GROUP BY repo_name, actor_login;