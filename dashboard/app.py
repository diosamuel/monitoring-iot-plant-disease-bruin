"""Streamlit dashboard for the Smart Plant Monitoring system.

Reads curated data from BigQuery for cloud analytics and falls back to
the local DuckDB staging file for fast near-real-time views.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd
import streamlit as st

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "/data/duckdb.db")
BQ_PROJECT = os.environ.get("BQ_PROJECT_ID", "your-gcp-project")
BQ_DATASET = os.environ.get("BQ_DATASET", "smart_plant")

st.set_page_config(
    page_title="Smart Plant Monitoring",
    page_icon="🌱",
    layout="wide",
)


@st.cache_resource
def duck_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DUCKDB_PATH, read_only=True)


@st.cache_resource
def bq_client():
    try:
        from google.cloud import bigquery

        return bigquery.Client(project=BQ_PROJECT)
    except Exception:  # noqa: BLE001
        return None


@st.cache_data(ttl=30)
def load_recent_sensors(hours: int) -> pd.DataFrame:
    con = duck_conn()
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    try:
        return con.execute(
            """
            SELECT event_ts, plant_id, temperature, humidity, soil_moisture
            FROM raw_sensor_events
            WHERE event_ts >= ?
            ORDER BY event_ts
            """,
            [since],
        ).fetch_df()
    except duckdb.CatalogException:
        return pd.DataFrame()


@st.cache_data(ttl=30)
def load_recent_predictions(hours: int) -> pd.DataFrame:
    con = duck_conn()
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    try:
        return con.execute(
            """
            SELECT event_ts, plant_id, label, score
            FROM raw_prediction_events
            WHERE event_ts >= ?
            ORDER BY event_ts DESC
            """,
            [since],
        ).fetch_df()
    except duckdb.CatalogException:
        return pd.DataFrame()


def render_kpis(sensors: pd.DataFrame) -> None:
    col_a, col_b, col_c, col_d = st.columns(4)
    if sensors.empty:
        col_a.metric("Plants", 0)
        col_b.metric("Avg Temp (°C)", "—")
        col_c.metric("Avg Humidity (%)", "—")
        col_d.metric("Avg Soil", "—")
        return

    col_a.metric("Plants", sensors["plant_id"].nunique())
    col_b.metric("Avg Temp (°C)", f"{sensors['temperature'].mean():.1f}")
    col_c.metric("Avg Humidity (%)", f"{sensors['humidity'].mean():.1f}")
    col_d.metric("Avg Soil", f"{sensors['soil_moisture'].mean():.0f}")


def main() -> None:
    st.title("🌱 Smart Plant Monitoring")
    st.caption(
        "Edge inference on Raspberry Pi · MQTT · DuckDB staging · BigQuery analytics"
    )

    with st.sidebar:
        st.header("Filters")
        hours = st.slider("Time window (hours)", 1, 72, 6)
        st.markdown(f"**BigQuery:** `{BQ_PROJECT}.{BQ_DATASET}`")
        st.markdown(f"**DuckDB:** `{DUCKDB_PATH}`")

    sensors = load_recent_sensors(hours)
    predictions = load_recent_predictions(hours)

    render_kpis(sensors)

    st.subheader("Environmental trends")
    if sensors.empty:
        st.info("No sensor data yet. Waiting for ESP32 readings via MQTT.")
    else:
        chart = sensors.set_index("event_ts")[
            ["temperature", "humidity", "soil_moisture"]
        ]
        st.line_chart(chart)

    st.subheader("Recent disease predictions")
    if predictions.empty:
        st.info("No predictions yet. Waiting for ESP32-CAM + TFLite inference.")
    else:
        st.dataframe(predictions, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
