
CREATE OR REPLACE TABLE `learngcp-461809.silver.sensor` (
  filename STRING NOT NULL,
  event_time TIMESTAMP NOT NULL,
  temperature FLOAT64,
  humidity FLOAT64,
  soil_moisture FLOAT64
);

CREATE OR REPLACE TABLE `learngcp-461809.silver.image` (
  filename STRING NOT NULL,
  event_time TIMESTAMP NOT NULL,
  plant_type STRING,
  health_status STRING,
  confidence FLOAT64,
  severity FLOAT64,
  summary STRING,
  possible_issues STRING,
  recommendations STRING,
  heatmap STRING
);

CREATE OR REPLACE TABLE `learngcp-461809.silver.weather` (
  id INT64 NOT NULL,
  adm4 STRING NOT NULL,
  provinsi STRING,
  kotkab STRING,
  kecamatan STRING,
  desa STRING,
  lon FLOAT64,
  lat FLOAT64,
  timezone STRING,
  datetime_utc TIMESTAMP NOT NULL,
  datetime_local TIMESTAMP,
  analysis_date TIMESTAMP,
  time_index STRING,
  temperature FLOAT64,
  total_cloud_cover FLOAT64,
  precipitation_mm FLOAT64,
  humidity FLOAT64 NOT NULL,
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

CREATE OR REPLACE TABLE `learngcp-461809.gold.weather_forecast` (
  forecast_date DATE NOT NULL,
  adm4 STRING NOT NULL,
  provinsi STRING,
  kotkab STRING,
  kecamatan STRING,
  desa STRING,
  lon FLOAT64,
  lat FLOAT64,
  timezone STRING,
  forecast_count INT64,
  avg_temperature FLOAT64,
  min_temperature FLOAT64,
  max_temperature FLOAT64,
  avg_humidity FLOAT64,
  total_precipitation_mm FLOAT64,
  avg_cloud_cover FLOAT64,
  avg_wind_speed FLOAT64,
  min_visibility_meters FLOAT64,
  ingested_at TIMESTAMP
);

CREATE OR REPLACE TABLE `learngcp-461809.gold.sensor_readings` (
  filename STRING NOT NULL,
  reading_count INT64,
  first_reading_at TIMESTAMP NOT NULL,
  last_reading_at TIMESTAMP,
  avg_temperature FLOAT64,
  min_temperature FLOAT64,
  max_temperature FLOAT64,
  avg_humidity FLOAT64,
  min_humidity FLOAT64,
  max_humidity FLOAT64,
  avg_soil_moisture FLOAT64,
  min_soil_moisture FLOAT64,
  max_soil_moisture FLOAT64,
  ingested_at TIMESTAMP
);

CREATE OR REPLACE TABLE `learngcp-461809.gold.plant_health` (
  filename STRING NOT NULL,
  event_time TIMESTAMP NOT NULL,
  plant_type STRING,
  health_status STRING,
  confidence FLOAT64,
  severity FLOAT64,
  summary STRING,
  possible_issues STRING,
  recommendations STRING,
  heatmap STRING,
  reading_count INT64,
  avg_temperature FLOAT64,
  avg_humidity FLOAT64,
  avg_soil_moisture FLOAT64,
  ingested_at TIMESTAMP
);
