/*@bruin
name: raw.sensor
type: duckdb.sql
connection: duckdb-sensor

columns:
  - name: temp
    type: float
  - name: humid
    type: float
  - name: soil
    type: float
  - name: filename
    type: string
  - name: event_time
    type: timestamp
@bruin */

SELECT
    CAST(temp AS FLOAT) AS temp,
    CAST(humid AS FLOAT) AS humid,
    CAST(soil AS FLOAT) AS soil,
    CAST(filename AS VARCHAR) AS filename,
    CAST(event_time AS TIMESTAMP) AS event_time
FROM read_json_auto('stg_sensor.jsonl');