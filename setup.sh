echo "setup db"
duckdb -c ".read stg_sensor.sql;insert into sensor select * from read_json_auto('stg_sensor.jsonl');" stg_sensor.duckdb
duckdb -c ".read stg_image.sql" stg_image.duckdb
duckdb -c ".read stg_weather.sql" stg_weather.duckdb

echo "listen on 1883"
uv run mosquitto/subscribe.py
