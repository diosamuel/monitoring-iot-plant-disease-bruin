CREATE TABLE `learngcp-461809.silver.weather` (
  id STRING,
  adm4 STRING,
  provinsi STRING,
  kotkab STRING,
  kecamatan STRING,
  desa STRING,
  lon FLOAT64,
  lat FLOAT64,
  timezone STRING,

  datetime_utc TIMESTAMP,
  datetime_local TIMESTAMP,
  analysis_date TIMESTAMP,
  time_index STRING,

  temperature FLOAT64,
  total_cloud_cover FLOAT64,
  precipitation_mm FLOAT64,
  humidity FLOAT64,
  wind_speed FLOAT64,
  wind_direction_deg FLOAT64,

  wind_from STRING,
  wind_to STRING,

  visibility_meters FLOAT64,
  visibility_text STRING,

  weather_code INT64,
  weather_desc STRING,
  weather_desc_en STRING,

  image_url STRING
);


CREATE OR REPLACE TABLE `learngcp-461809.silver.sensor` (
  filename STRING,
  event_time TIMESTAMP,

  temperature FLOAT64,
  humidity FLOAT64,
  soil_moisture FLOAT64,

  ingested_at TIMESTAMP
);

CREATE OR REPLACE TABLE `learngcp-461809.silver.image` (
  filename STRING,
  event_time TIMESTAMP,

  plant_type STRING,
  health_status STRING,
  confidence FLOAT64,
  severity FLOAT64,

  summary STRING,

  possible_issues STRING,
  recommendations STRING,

  temperature FLOAT64,
  humidity FLOAT64,
  soil_moisture FLOAT64,

  ingested_at TIMESTAMP
);