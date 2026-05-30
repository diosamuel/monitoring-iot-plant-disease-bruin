/* @bruin

name: raw.image_analytics
type: duckdb.sql
connection: duckdb-image
materialization:
  type: table

columns:
  - name: filename
    type: varchar
  - name: plant_type
    type: varchar
  - name: health_status
    type: varchar
  - name: confidence
    type: double
  - name: severity
    type: double
  - name: summary
    type: varchar
  - name: possible_issues
    type: varchar
  - name: recommendations
    type: varchar
  - name: event_time
    type: timestamp

@bruin */

SELECT
    filename,
    status,
    json_extract_string(response::JSON, '$.plant_type')       AS plant_type,
    json_extract_string(response::JSON, '$.health_status')    AS health_status,
    CAST(json_extract_string(response::JSON, '$.confidence') AS DOUBLE)  AS confidence,
    CAST(json_extract_string(response::JSON, '$.severity') AS DOUBLE)    AS severity,
    json_extract_string(response::JSON, '$.summary')          AS summary,
    json_extract(response::JSON, '$.possible_issues')::VARCHAR   AS possible_issues,
    json_extract(response::JSON, '$.recommendations')::VARCHAR   AS recommendations,
    CURRENT_TIMESTAMP AS event_time
FROM read_json('sources/image-analytics.jsonl',
    columns={
        status: 'VARCHAR',
        filename: 'VARCHAR',
        path: 'VARCHAR',
        model: 'VARCHAR',
        bytes: 'BIGINT',
        response: 'VARCHAR'
    },
    format='newline_delimited'
)
WHERE status = 'success'
