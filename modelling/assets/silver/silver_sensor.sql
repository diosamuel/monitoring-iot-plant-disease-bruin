/* @bruin

name: silver.sensor
type: duckdb.sql
connection: duckdb-sensor
materialization:
  type: table

depends:
  - raw.sensor

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

custom_checks:
  - name: row count is greater than zero
    description: ensures the table is not empty
    query: SELECT count(*) > 0 FROM silver.sensor
    value: 1

@bruin */

SELECT
    filename,
    event_time,
    temp   AS temperature,
    humid  AS humidity,
    soil   AS soil_moisture
FROM sensor
WHERE event_time IS NOT NULL
