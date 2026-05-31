# Smart Plant Monitoring — IoT Data Warehouse

An IoT-based smart plant monitoring system that combines edge computing,
AI inference, and cloud analytics using ESP32 devices, a Raspberry Pi
edge node, a VPS with DuckDB + Bruin pipelines, and BigQuery.

---

## Overview

Plant conditions are monitored in near real-time using IoT sensors and
image-based disease detection powered by Gemini Vision. The architecture
is split across three layers so each device only does work that fits its
resource budget:

- **ESP32 / ESP32-CAM** — data acquisition (sensors + camera)
- **Raspberry Pi 3B** — edge computing (MQTT ingest, preprocessing)
- **VPS** — message broker, staging DB, Bruin data pipeline
- **BigQuery** — analytical data warehouse (gold layer)
- **Streamlit** — operator dashboard

---

## System Architecture

![architecture](./architecture.png)

---

## Data Pipeline (Bruin)

The pipeline follows a **medallion architecture** (raw → silver → gold)
with full lineage tracking. Runs every 12 hours (`0 */12 * * *`).

### Layers

| Layer  | Storage  | Connection        | Description                              |
|--------|----------|-------------------|------------------------------------------|
| Raw    | DuckDB   | per-domain        | `read_json_auto` from JSONL sources      |
| Silver | DuckDB   | per-domain        | Cleaned, joined, normalized tables       |
| Silver | BigQuery | gcp-default       | Ingested via `ingestr` (replace strategy) |
| Gold   | BigQuery | gcp-default       | Aggregated analytics-ready tables        |

### Gold Tables

| Table                    | Description                                         |
|--------------------------|-----------------------------------------------------|
| `gold.sensor_readings`   | Aggregated sensor stats per image (avg/min/max)     |
| `gold.plant_health`      | Image predictions + aggregated sensor environment   |
| `gold.weather_forecast`  | Daily weather summary per location                  |

### Running the Pipeline

```bash
# Full pipeline (all layers)
bruin run modelling/

# Single asset
bruin run modelling/assets/silver/silver_sensor.sql

# Ingest silver to BigQuery
bruin run modelling/assets/silver/silver_sensor.asset.yml

# Gold layer only
bruin run modelling/assets/gold/gold_sensor_readings.sql

# View lineage
bruin lineage modelling/
```

---

## Staging Sources

| File                     | DuckDB Connection | Raw Table            | Source                        |
|--------------------------|-------------------|----------------------|-------------------------------|
| `esp32_sensor.jsonl`     | duckdb-sensor     | `raw.sensor`         | ESP32 DHT11 + soil via MQTT   |
| `image-log.jsonl`        | duckdb-image      | `raw.image_log`      | ESP32-CAM capture timestamps  |
| `image-analytics.jsonl`  | duckdb-image      | `raw.image_analytics`| Gemini Vision predictions     |
| `bmkg_weather.jsonl`     | duckdb-weather    | `raw.bmkg_weather`   | BMKG weather API (JSON)       |

---

## Simulators

Scripts in `simulate/` populate JSONL source files for local development:

```bash
python simulate/weather.py      # Fetch BMKG forecast → sources/bmkg_weather.jsonl
python simulate/dht22_soil.py   # Simulate sensor readings → sources/esp32_sensor.jsonl
python simulate/cam.py          # Simulate camera capture → sources/image-log.jsonl
```

---

## BigQuery Schema

The `schema/bq.sql` file contains `CREATE OR REPLACE TABLE` statements
for all silver and gold tables in BigQuery under project `learngcp-461809`:

- `learngcp-461809.silver.sensor`
- `learngcp-461809.silver.image`
- `learngcp-461809.silver.weather`
- `learngcp-461809.gold.sensor_readings`
- `learngcp-461809.gold.plant_health`
- `learngcp-461809.gold.weather_forecast`

---

## Configuration

```bash
cp .env.example .env
```

| Variable         | Default             | Used by                     |
|------------------|---------------------|-----------------------------|
| `BQ_PROJECT_ID`  | `your-gcp-project`  | Gold layer, Dashboard       |
| `BQ_DATASET`     | `smart_plant`       | Gold layer, Dashboard       |
| `GEMINI_API_KEY` | —                   | API prediction service      |
| `GEMINI_MODEL`   | `gemini-2.5-flash`  | API prediction service      |

Place your Google service account JSON at `./secrets/gcp-secrets.json`.

Bruin connections are configured in `.bruin.yml`:
- `gcp-default` — BigQuery (project: `learngcp-461809`)
- `duckdb-sensor` — `modelling/assets/staging/stg_sensor.duckdb`
- `duckdb-image` — `modelling/assets/staging/stg_image.duckdb`
- `duckdb-weather` — `modelling/assets/staging/stg_weather.duckdb`

---

## Technology Stack

| Category         | Technology                    |
|------------------|-------------------------------|
| IoT Devices      | ESP32, ESP32-CAM              |
| Sensors          | DHT11, Soil Moisture (ADC)    |
| Edge Computing   | Raspberry Pi 3B               |
| AI Inference     | Gemini 2.5 Flash (Vision)     |
| Messaging        | MQTT (Mosquitto)              |
| Staging Database | DuckDB                        |
| Data Pipeline    | Bruin                         |
| Data Warehouse   | Google BigQuery               |
| Dashboard        | Streamlit                     |
| Package Manager  | uv (Python)                   |
