import json
import os
import duckdb
import requests

BMKG_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
ADM4 = "18.71.02.1003"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "sources", "stg_weather.duckdb")

# Fetch
resp = requests.get(BMKG_URL, params={"adm4": ADM4}, timeout=30)
resp.raise_for_status()
data = resp.json()

# Extract lokasi
lokasi = data["lokasi"]

# Store
con = duckdb.connect(DB_PATH)
con.execute("""
    INSERT INTO bmkg_weather (adm1, adm2, adm3, adm4, provinsi, kotkab, kecamatan, desa, lon, lat, timezone, weather_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", [
    lokasi["adm1"], lokasi["adm2"], lokasi["adm3"], lokasi["adm4"],
    lokasi["provinsi"], lokasi["kotkab"], lokasi["kecamatan"], lokasi["desa"],
    lokasi["lon"], lokasi["lat"], lokasi["timezone"],
    json.dumps(data),
])
con.close()

print(f"Stored weather for {lokasi['desa']}, {lokasi['kotkab']}")
