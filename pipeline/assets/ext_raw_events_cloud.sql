/* @bruin
name: ext_raw_events_cloud
type: bq.sql
@bruin */

CREATE OR REPLACE EXTERNAL TABLE `gharchive-491810.gharchive_dataset.ext_raw_events_cloud`
OPTIONS (
  format = 'PARQUET',
  uris = [
    'gs://gharchive-491810-bucket/raw/year={{ end_date[:4] }}/month={{ end_date[5:7] }}/day={{ end_date[8:10] }}/part-*'
  ]
);