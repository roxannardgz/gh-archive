/* @bruin
name: ext_raw_events_cloud
type: bq.sql
depends:
  - download_gharchive_cloud
@bruin */

DECLARE start_date DATE DEFAULT DATE('{{ start_date }}');
DECLARE end_date DATE DEFAULT DATE('{{ end_date }}');

DECLARE uri_list STRING;

SET uri_list = (
  SELECT STRING_AGG(
    FORMAT(
      "'gs://gharchive-491810-bucket/raw/year=%d/month=%02d/day=%02d/part-*'",
      EXTRACT(YEAR FROM d),
      EXTRACT(MONTH FROM d),
      EXTRACT(DAY FROM d)
    ),
    ", "
  )
  FROM UNNEST(GENERATE_DATE_ARRAY(start_date, end_date)) AS d
);

EXECUTE IMMEDIATE FORMAT("""
  CREATE OR REPLACE EXTERNAL TABLE `gharchive-491810.gharchive_dataset.ext_raw_events_cloud`
  OPTIONS (
    format = 'PARQUET',
    uris = [%s]
  )
""", uri_list);