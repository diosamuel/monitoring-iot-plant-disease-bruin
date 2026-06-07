/* @bruin

name: gold.weather_forecast
type: bq.sql
materialization:
  type: table
  strategy: truncate+insert

depends:
  - silver.weather

columns:
  - name: forecast_date
    type: DATE
    description: forecast date (aggregation key)
    checks:
      - name: not_null
  - name: adm4
    type: STRING
    description: administrative level 4 code
    checks:
      - name: not_null
  - name: provinsi
    type: STRING
    description: province name
  - name: kotkab
    type: STRING
    description: city/regency name
  - name: kecamatan
    type: STRING
    description: district name
  - name: desa
    type: STRING
    description: village name
  - name: lon
    type: FLOAT64
    description: longitude
  - name: lat
    type: FLOAT64
    description: latitude
  - name: timezone
    type: STRING
    description: timezone string
  - name: forecast_count
    type: INT64
    description: number of forecast entries for this day
  - name: avg_temperature
    type: FLOAT64
    description: daily average temperature in Celsius
  - name: min_temperature
    type: FLOAT64
    description: daily minimum temperature in Celsius
  - name: max_temperature
    type: FLOAT64
    description: daily maximum temperature in Celsius
  - name: avg_humidity
    type: FLOAT64
    description: daily average humidity percentage
  - name: total_precipitation_mm
    type: FLOAT64
    description: total daily precipitation in mm
  - name: avg_cloud_cover
    type: FLOAT64
    description: daily average cloud cover percentage
  - name: avg_wind_speed
    type: FLOAT64
    description: daily average wind speed
  - name: min_visibility_meters
    type: FLOAT64
    description: minimum visibility in meters
  - name: ingested_at
    type: TIMESTAMP
    description: pipeline run timestamp
@bruin */

-- Gold layer: daily aggregated weather forecast
SELECT
    DATE(datetime_local)                          AS forecast_date,
    STRING(adm4)                                  AS adm4,
    STRING(provinsi)                              AS provinsi,
    STRING(kotkab)                                AS kotkab,
    STRING(kecamatan)                             AS kecamatan,
    STRING(desa)                                  AS desa,
    FLOAT64(lon)                                  AS lon,
    FLOAT64(lat)                                  AS lat,
    STRING(timezone)                              AS timezone,
    COUNT(*)                                      AS forecast_count,
    AVG(temperature)                              AS avg_temperature,
    MIN(temperature)                              AS min_temperature,
    MAX(temperature)                              AS max_temperature,
    AVG(humidity)                                 AS avg_humidity,
    SUM(precipitation_mm)                         AS total_precipitation_mm,
    AVG(total_cloud_cover)                        AS avg_cloud_cover,
    AVG(wind_speed)                               AS avg_wind_speed,
    MIN(visibility_meters)                        AS min_visibility_meters,
    CURRENT_TIMESTAMP()                           AS ingested_at
FROM silver.weather
GROUP BY
    DATE(datetime_local),
    STRING(adm4),
    STRING(provinsi),
    STRING(kotkab),
    STRING(kecamatan),
    STRING(desa),
    FLOAT64(lon),
    FLOAT64(lat),
    STRING(timezone)
