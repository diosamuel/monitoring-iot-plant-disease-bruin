/* @bruin

name: silver_duck.sensor
type: duckdb.sql
connection: duckdb-sensor
materialization:
  type: table

depends:
  - raw.sensor
  - raw.image_log

columns:
  - name: filename
    type: string
    description: image filename associated with this sensor reading
    checks:
      - name: not_null
  - name: event_time
    type: timestamp
    description: timestamp of the sensor reading
    checks:
      - name: not_null
  - name: temperature
    type: float
    description: temperature in Celsius (from DHT11)
  - name: humidity
    type: float
    description: relative humidity percentage (from DHT11)
  - name: soil_moisture
    type: float
    description: soil moisture raw ADC value
@bruin */

WITH image_log AS (
    SELECT
        CAST(filename AS VARCHAR)     AS filename,
        CAST(event_time AS TIMESTAMP) AS event_time
    FROM read_json_auto('sources/image-log.jsonl')
),
sensor AS (
    SELECT *
    FROM raw.sensor
    WHERE event_time IS NOT NULL
)
SELECT
    i.filename,
    s.event_time,
    s.temp   AS temperature,
    s.humid  AS humidity,
    s.soil   AS soil_moisture
FROM sensor s
ASOF JOIN image_log i
    ON s.event_time >= i.event_time
