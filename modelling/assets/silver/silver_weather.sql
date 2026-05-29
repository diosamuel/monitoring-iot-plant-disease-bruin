/* @bruin

name: silver.weather
type: duckdb.sql
connection: duckdb-weather
materialization:
  type: table

depends:
  - raw.bmkg_weather

columns:
  - name: id
    type: bigint
    description: source row id from bmkg_weather
    checks:
      - name: not_null
  - name: adm4
    type: varchar
    description: administrative level 4 code
    checks:
      - name: not_null
  - name: provinsi
    type: varchar
    description: province name
  - name: kotkab
    type: varchar
    description: city/regency name
  - name: kecamatan
    type: varchar
    description: district name
  - name: desa
    type: varchar
    description: village name
  - name: lon
    type: double
    description: longitude
  - name: lat
    type: double
    description: latitude
  - name: timezone
    type: varchar
    description: timezone string
  - name: datetime_utc
    type: timestamp
    description: forecast datetime in UTC
    checks:
      - name: not_null
  - name: datetime_local
    type: timestamp
    description: forecast datetime in local time
  - name: analysis_date
    type: timestamp
    description: analysis/issue date of the forecast
  - name: time_index
    type: varchar
    description: time index label (e.g. "12-13")
  - name: temperature
    type: double
    description: temperature in Celsius
  - name: total_cloud_cover
    type: double
    description: total cloud cover percentage
  - name: precipitation_mm
    type: double
    description: total precipitation in mm
  - name: humidity
    type: double
    description: humidity percentage
    checks:
      - name: not_null
  - name: wind_speed
    type: double
    description: wind speed
  - name: wind_direction_deg
    type: double
    description: wind direction in degrees
  - name: wind_from
    type: varchar
    description: wind from direction
  - name: wind_to
    type: varchar
    description: wind to direction
  - name: visibility_meters
    type: double
    description: visibility in meters
  - name: visibility_text
    type: varchar
    description: visibility description text
  - name: weather_code
    type: integer
    description: BMKG weather code
  - name: weather_desc
    type: varchar
    description: weather description (Indonesian)
  - name: weather_desc_en
    type: varchar
    description: weather description (English)
  - name: image_url
    type: varchar
    description: weather icon URL

custom_checks:
  - name: row count is greater than zero
    description: ensures the table is not empty after transformation
    query: SELECT count(*) > 0 FROM silver.weather
    value: 1
  - name: no duplicate forecast per location and time
    description: ensures uniqueness on (adm4, datetime_utc)
    query: SELECT count(*) FROM (SELECT adm4, datetime_utc FROM silver.weather GROUP BY 1, 2 HAVING count(*) > 1)
    value: 0

@bruin */

WITH source AS (
    SELECT
        id, adm4, provinsi, kotkab, kecamatan, desa, lon, lat, timezone, weather_data
    FROM bmkg_weather
    WHERE weather_data IS NOT NULL
),
data_entries AS (
    SELECT
        s.id, s.adm4, s.provinsi, s.kotkab, s.kecamatan, s.desa, s.lon, s.lat, s.timezone,
        unnest(from_json(s.weather_data->'data', '["json"]')) AS data_entry
    FROM source s
),
cuaca_days AS (
    SELECT
        d.id, d.adm4, d.provinsi, d.kotkab, d.kecamatan, d.desa, d.lon, d.lat, d.timezone,
        unnest(from_json(d.data_entry->'cuaca', '["json"]')) AS cuaca_day
    FROM data_entries d
),
cuaca_items AS (
    SELECT
        c.id, c.adm4, c.provinsi, c.kotkab, c.kecamatan, c.desa, c.lon, c.lat, c.timezone,
        unnest(from_json(c.cuaca_day, '["json"]')) AS item
    FROM cuaca_days c
)
SELECT
    ci.id,
    ci.adm4,
    ci.provinsi,
    ci.kotkab,
    ci.kecamatan,
    ci.desa,
    ci.lon,
    ci.lat,
    ci.timezone,
    CAST(ci.item->>'utc_datetime' AS TIMESTAMP)       AS datetime_utc,
    CAST(ci.item->>'local_datetime' AS TIMESTAMP)     AS datetime_local,
    CAST(ci.item->>'analysis_date' AS TIMESTAMP)      AS analysis_date,
    ci.item->>'time_index'                            AS time_index,
    CAST(ci.item->>'t' AS DOUBLE)                     AS temperature,
    CAST(ci.item->>'tcc' AS DOUBLE)                   AS total_cloud_cover,
    CAST(ci.item->>'tp' AS DOUBLE)                    AS precipitation_mm,
    CAST(ci.item->>'hu' AS DOUBLE)                    AS humidity,
    CAST(ci.item->>'ws' AS DOUBLE)                    AS wind_speed,
    CAST(ci.item->>'wd_deg' AS DOUBLE)                AS wind_direction_deg,
    ci.item->>'wd'                                    AS wind_from,
    ci.item->>'wd_to'                                 AS wind_to,
    CAST(ci.item->>'vs' AS DOUBLE)                    AS visibility_meters,
    ci.item->>'vs_text'                               AS visibility_text,
    CAST(ci.item->>'weather' AS INTEGER)              AS weather_code,
    ci.item->>'weather_desc'                          AS weather_desc,
    ci.item->>'weather_desc_en'                       AS weather_desc_en,
    ci.item->>'image'                                 AS image_url
FROM cuaca_items ci
