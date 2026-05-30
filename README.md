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
- **Raspberry Pi 3B** — edge computing (TFLite inference, preprocessing)
- **VPS** — message broker, staging DB, Bruin data pipeline, ETL
- **BigQuery** — analytical data warehouse
- **Streamlit** — operator dashboard

---

## System Architecture

![architecture](./architecture.png)

```text
ESP32 / ESP32-CAM
        │
        ▼
Raspberry Pi 3B (edge inference, TFLite)
        │  MQTT
        ▼
VPS
 ├─ Mosquitto (broker)
 ├─ Ingestor  (MQTT → DuckDB)
 ├─ DuckDB    (staging: sources/)
 ├─ Bruin     (raw → silver → gold)
 └─ ETL       (gold → BigQuery)
        │
        ▼
BigQuery  ──►  Streamlit Dashboard
```

---

## Project Structure

```
├── api/                    # FastAPI prediction service (Gemini Vision)
│   ├── index.py
│   ├── system_prompt.txt
│   ├── preprocess/         # Image preprocessing
│   └── images/             # Captured images (gitignored)
├── esp32/                  # Device firmware
│   ├── esp32cam/           # Camera web server
│   └── sensor/             # DHT11 + soil moisture
├── mosquitto/              # MQTT broker config
│   ├── config/
│   └── subscribe.py
├── sources/                # DuckDB staging databases + schemas
│   ├── stg_sensor.duckdb
│   ├── stg_sensor.sql
│   ├── stg_image.duckdb
│   ├── stg_image.sql
│   ├── stg_weather.duckdb
│   └── stg_weather.sql
├── modelling/              # Bruin data pipeline
│   ├── pipeline.yml
│   ├── assets/
│   │   ├── raw/            # Source declarations (lineage entry points)
│   │   ├── silver/         # DuckDB transformations
│   │   └── gold/           # BigQuery output tables
│   └── logs/
├── simulate/               # Simulator scripts for testing
│   ├── cam.py              # Camera capture simulator
│   ├── dht22.py            # Temperature/humidity simulator
│   ├── soil.py             # Soil moisture simulator
│   └── weather.py          # BMKG weather API fetcher
├── secrets/                # GCP service account (gitignored)
├── docker-compose.yaml
├── .bruin.yml              # Bruin connections config (gitignored)
└── .env.example
```

---

## Data Pipeline (Bruin)

The pipeline follows a **medallion architecture** (raw → silver → gold)
with full lineage tracking:

```
raw.sensor ──────────→ silver.sensor ──────→ gold.sensor_readings
                                        └──→ gold.plant_health
raw.image_log ───────┐
raw.image_analytics ─┴→ silver.image ──────→ gold.plant_health

raw.bmkg_weather ────→ silver.weather ─────→ gold.weather_forecast
```

| Layer  | Storage | Description |
|--------|---------|-------------|
| Raw    | DuckDB  | Source declarations for staging tables |
| Silver | DuckDB  | Cleaned, renamed, normalized tables |
| Gold   | BigQuery | Analytics-ready tables for dashboard |

### Running the pipeline

```bash
# Run from project root
cd /path/to/smart-plant-monitoring

# Run full pipeline
bruin run modelling/

# Run a single asset
bruin run modelling/assets/silver/silver_weather.sql

# View lineage
bruin lineage modelling/
```

---

## Staging Tables

| Table | Database | Source |
|-------|----------|--------|
| `sensor` | `stg_sensor.duckdb` | ESP32 DHT11 + soil via MQTT |
| `image_log` | `stg_image.duckdb` | ESP32-CAM captures |
| `image_analytics` | `stg_image.duckdb` | Gemini Vision predictions |
| `bmkg_weather` | `stg_weather.duckdb` | BMKG weather API (JSON) |

---

## Simulators

Scripts in `simulate/` populate staging databases for local development:

```bash
python simulate/weather.py    # Fetch BMKG forecast → stg_weather.duckdb
python simulate/dht22.py      # Simulate sensor readings → stg_sensor.duckdb
python simulate/soil.py       # Simulate soil moisture → stg_sensor.duckdb
python simulate/cam.py        # Simulate camera capture → stg_image.duckdb
```

---

## Configuration

```bash
cp .env.example .env
```

| Variable | Default | Used by |
|----------|---------|---------|
| `BQ_PROJECT_ID` | `your-gcp-project` | Gold layer, ETL, Dashboard |
| `BQ_DATASET` | `smart_plant` | Gold layer, ETL, Dashboard |
| `GEMINI_API_KEY` | — | API prediction service |
| `GEMINI_MODEL` | `gemini-2.5-flash` | API prediction service |

Place your Google service account JSON at `./secrets/gcp-sa.json`.

---

## Docker Compose Services

| Service | Port | Role |
|---------|------|------|
| `mosquitto` | 1883, 9001 | MQTT broker |
| `ingestor` | — | MQTT → DuckDB |
| `bruin` | — | One-shot pipeline run |
| `etl` | — | DuckDB gold → BigQuery |
| `dashboard` | 8501 | Streamlit UI |


---

## Technology Stack

| Category | Technology |
|----------|-----------|
| IoT Devices | ESP32, ESP32-CAM |
| Sensors | DHT11, Soil Moisture |
| Edge Computing | Raspberry Pi 3B |
| AI Inference | TensorFlow Lite, Gemini Vision |
| Messaging | MQTT (Mosquitto) |
| Staging Database | DuckDB |
| Data Pipeline | Bruin |
| Data Warehouse | Google BigQuery |
| Dashboard | Streamlit |
| Orchestration | Docker Compose |
