CREATE SEQUENCE IF NOT EXISTS seq_bmkg_weather_id START 1;
CREATE TABLE IF NOT EXISTS bmkg_weather (
  id BIGINT PRIMARY KEY DEFAULT nextval('seq_bmkg_weather_id'),
  adm1 VARCHAR(16),
  adm2 VARCHAR(16),
  adm3 VARCHAR(16),
  adm4 VARCHAR(32),
  provinsi VARCHAR(128),
  kotkab VARCHAR(128),
  kecamatan VARCHAR(128),
  desa VARCHAR(128),
  lon DOUBLE,
  lat DOUBLE,
  timezone VARCHAR(32),
  weather_data JSON,
);