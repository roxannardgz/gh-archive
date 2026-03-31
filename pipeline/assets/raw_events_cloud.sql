/* @bruin
name: raw_events_cloud
type: bq.sql
depends:
  - ext_raw_events_cloud
@bruin */

DECLARE target_date DATE DEFAULT DATE('{{ end_date }}');

CREATE TABLE IF NOT EXISTS `gharchive-491810.gharchive_dataset.raw_events`
PARTITION BY DATE(created_at) AS
SELECT *
FROM `gharchive-491810.gharchive_dataset.ext_raw_events_cloud`
WHERE FALSE;

DELETE FROM `gharchive-491810.gharchive_dataset.raw_events`
WHERE DATE(created_at) = target_date;

INSERT INTO `gharchive-491810.gharchive_dataset.raw_events`
SELECT *
FROM `gharchive-491810.gharchive_dataset.ext_raw_events_cloud`
WHERE DATE(created_at) = target_date;