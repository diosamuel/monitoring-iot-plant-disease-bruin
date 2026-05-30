/* @bruin

name: raw.bmkg_weather
type: duckdb.sql
connection: duckdb-weather
materialization:
  type: table

columns:
  - name: id
    type: bigint
  - name: adm1
    type: varchar
  - name: adm2
    type: varchar
  - name: adm3
    type: varchar
  - name: adm4
    type: varchar
  - name: provinsi
    type: varchar
  - name: kotkab
    type: varchar
  - name: kecamatan
    type: varchar
  - name: desa
    type: varchar
  - name: lon
    type: double
  - name: lat
    type: double
  - name: timezone
    type: varchar
  - name: weather_data
    type: json

@bruin */

SELECT
    ROW_NUMBER() OVER () AS id,
    adm1,
    adm2,
    adm3,
    adm4,
    provinsi,
    kotkab,
    kecamatan,
    desa,
    lon,
    lat,
    timezone,
    weather_data
FROM read_json_auto('sources/bmkg_weather.jsonl', maximum_depth=1)
