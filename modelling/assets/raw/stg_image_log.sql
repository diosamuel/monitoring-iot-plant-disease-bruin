/* @bruin

name: raw.image_log
type: duckdb.sql
connection: duckdb-image
materialization:
  type: table
  strategy: create+replace

columns:
  - name: filename
    type: varchar
    description: image filename (matches sensor.filename)
    checks:
      - name: not_null
  - name: event_time
    type: timestamp
    description: timestamp when the image was captured
    checks:
      - name: not_null

@bruin */

SELECT
    CAST(filename AS VARCHAR)     AS filename,
    CAST(event_time AS TIMESTAMP) AS event_time
FROM read_json_auto('sources/image-log.jsonl')
