/* @bruin

name: gold.sensor_readings
type: bq.sql
materialization:
  type: table

depends:
  - silver.sensor

columns:
  - name: filename
    type: STRING
    description: image filename associated with this reading
    checks:
      - name: not_null
  - name: event_time
    type: TIMESTAMP
    description: timestamp of the sensor reading
    checks:
      - name: not_null
  - name: temperature
    type: FLOAT64
    description: temperature in Celsius
  - name: humidity
    type: FLOAT64
    description: relative humidity percentage
  - name: soil_moisture
    type: FLOAT64
    description: soil moisture raw ADC value
  - name: ingested_at
    type: TIMESTAMP
    description: pipeline run timestamp

custom_checks:
  - name: row count is greater than zero
    query: SELECT count(*) > 0 FROM gold.sensor_readings
    value: 1

@bruin */

SELECT
    filename,
    event_time,
    temperature,
    humidity,
    soil_moisture,
    CURRENT_TIMESTAMP AS ingested_at
FROM silver.sensor
