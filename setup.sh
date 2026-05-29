echo "setup db"
duckdb -c ".read stg_sensor.sql" stg_sensor.duckdb
duckdb -c ".read stg_image.sql" stg_image.duckdb
duckdb -c ".read stg_weather.sql" stg_weather.duckdb

echo "listen on 1883"
uv run mosquitto/subscribe.py