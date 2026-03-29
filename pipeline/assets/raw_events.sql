/* @bruin
name: raw_events
type: duckdb.sql
depends:
  - download_gharchive
materialization:
  type: table
@bruin */

SELECT *
FROM read_ndjson(
    'data/raw/*.json.gz',
    sample_size = -1,
    filename = true
);