/* @bruin

name: gold.weather_forecast
type: bq.sql
materialization:
  type: table

depends:
  - silver.weather

columns:
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
  - name: datetime_utc
    type: TIMESTAMP
    description: forecast datetime in UTC
    checks:
      - name: not_null
  - name: datetime_local
    type: TIMESTAMP
    description: forecast datetime in local time
  - name: analysis_date
    type: TIMESTAMP
    description: analysis/issue date
  - name: temperature
    type: FLOAT64
    description: temperature in Celsius
  - name: total_cloud_cover
    type: FLOAT64
    description: total cloud cover percentage
  - name: precipitation_mm
    type: FLOAT64
    description: total precipitation in mm
  - name: humidity
    type: FLOAT64
    description: humidity percentage
  - name: wind_speed
    type: FLOAT64
    description: wind speed
  - name: wind_direction_deg
    type: FLOAT64
    description: wind direction in degrees
  - name: wind_from
    type: STRING
    description: wind from direction
  - name: wind_to
    type: STRING
    description: wind to direction
  - name: visibility_meters
    type: FLOAT64
    description: visibility in meters
  - name: weather_code
    type: INT64
    description: BMKG weather code
  - name: weather_desc
    type: STRING
    description: weather description (Indonesian)
  - name: weather_desc_en
    type: STRING
    description: weather description (English)
  - name: ingested_at
    type: TIMESTAMP
    description: pipeline run timestamp

custom_checks:
  - name: row count is greater than zero
    query: SELECT count(*) > 0 FROM gold.weather_forecast
    value: 1

@bruin */

SELECT
    adm4,
    provinsi,
    kotkab,
    kecamatan,
    desa,
    lon,
    lat,
    timezone,
    datetime_utc,
    datetime_local,
    analysis_date,
    temperature,
    total_cloud_cover,
    precipitation_mm,
    humidity,
    wind_speed,
    wind_direction_deg,
    wind_from,
    wind_to,
    visibility_meters,
    weather_code,
    weather_desc,
    weather_desc_en,
    CURRENT_TIMESTAMP AS ingested_at
FROM silver.weather
