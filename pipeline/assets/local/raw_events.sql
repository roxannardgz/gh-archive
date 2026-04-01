/* @bruin
name: raw_events
type: duckdb.sql
depends:
  - download_gharchive_local
materialization:
  type: table

custom_checks:
  - name: row count greater than zero
    description: raw_events should not be empty
    query: SELECT COUNT(*) > 0 FROM raw_events
    value: 1

  - name: created_at not null
    description: all rows should have a timestamp
    query: SELECT COUNT(*) = COUNT(created_at) FROM raw_events
    value: 1

@bruin */

SELECT *
FROM read_ndjson(
    'data/raw/*.json.gz',
    sample_size = -1,
    union_by_name = true,
    filename = true
);