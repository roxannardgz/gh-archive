CREATE OR REPLACE TABLE raw_events AS
SELECT *
FROM read_ndjson(
    'data/raw/*.json.gz',
    sample_size = -1,
    filename = true
);