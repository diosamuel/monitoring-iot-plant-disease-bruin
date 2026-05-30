import json
import os

import requests

BMKG_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
ADM4 = "18.71.02.1003"
JSONL_PATH = os.path.join(os.path.dirname(__file__), "..", "sources", "stg_weather.jsonl")

# Fetch
resp = requests.get(BMKG_URL, params={"adm4": ADM4}, timeout=30)
resp.raise_for_status()
data = resp.json()

# Extract lokasi
lokasi = data["lokasi"]

# Store as JSONL
row = {
    "adm1": lokasi["adm1"],
    "adm2": lokasi["adm2"],
    "adm3": lokasi["adm3"],
    "adm4": lokasi["adm4"],
    "provinsi": lokasi["provinsi"],
    "kotkab": lokasi["kotkab"],
    "kecamatan": lokasi["kecamatan"],
    "desa": lokasi["desa"],
    "lon": lokasi["lon"],
    "lat": lokasi["lat"],
    "timezone": lokasi["timezone"],
    "weather_data": data,
}

with open(JSONL_PATH, "a") as f:
    f.write(json.dumps(row) + "\n")

print(f"Stored weather for {lokasi['desa']}, {lokasi['kotkab']}")
