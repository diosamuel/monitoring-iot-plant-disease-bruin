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
    description: image filename (aggregation key, one row per image)
    checks:
      - name: not_null
      - name: unique
  - name: reading_count
    type: INT64
    description: number of sensor readings in this period
  - name: first_reading_at
    type: TIMESTAMP
    description: earliest sensor reading timestamp
    checks:
      - name: not_null
  - name: last_reading_at
    type: TIMESTAMP
    description: latest sensor reading timestamp
  - name: avg_temperature
    type: FLOAT64
    description: average temperature in Celsius
  - name: min_temperature
    type: FLOAT64
    description: minimum temperature in Celsius
  - name: max_temperature
    type: FLOAT64
    description: maximum temperature in Celsius
  - name: avg_humidity
    type: FLOAT64
    description: average relative humidity percentage
  - name: min_humidity
    type: FLOAT64
    description: minimum relative humidity percentage
  - name: max_humidity
    type: FLOAT64
    description: maximum relative humidity percentage
  - name: avg_soil_moisture
    type: FLOAT64
    description: average soil moisture raw ADC value
  - name: min_soil_moisture
    type: FLOAT64
    description: minimum soil moisture raw ADC value
  - name: max_soil_moisture
    type: FLOAT64
    description: maximum soil moisture raw ADC value
  - name: ingested_at
    type: TIMESTAMP
    description: pipeline run timestamp
@bruin */

-- Gold layer: aggregate sensor readings per image capture period
SELECT
    filename,
    COUNT(*)                    AS reading_count,
    MIN(event_time)            AS first_reading_at,
    MAX(event_time)            AS last_reading_at,
    AVG(temperature)           AS avg_temperature,
    MIN(temperature)           AS min_temperature,
    MAX(temperature)           AS max_temperature,
    AVG(humidity)              AS avg_humidity,
    MIN(humidity)              AS min_humidity,
    MAX(humidity)              AS max_humidity,
    AVG(soil_moisture)         AS avg_soil_moisture,
    MIN(soil_moisture)         AS min_soil_moisture,
    MAX(soil_moisture)         AS max_soil_moisture,
    CURRENT_TIMESTAMP()        AS ingested_at
FROM silver.sensor
GROUP BY filename
