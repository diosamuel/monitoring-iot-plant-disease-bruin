"""BigQuery data access for the Smart Plant dashboard.

Reads from the gold layer (gold_edw.*) using the service account file
configured for the Bruin pipeline.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = os.getenv("BQ_PROJECT_ID", "learngcp-461809")
DATASET = os.getenv("BQ_DATASET", "gold_edw")
SERVICE_ACCOUNT_FILE = os.getenv(
    "GCP_SERVICE_ACCOUNT_FILE",
    str(Path(__file__).resolve().parents[1] / "secrets" / "gcp-secrets.json"),
)


@lru_cache(maxsize=1)
def _client() -> bigquery.Client:
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=creds)


def _query(sql: str) -> pd.DataFrame:
    return _client().query(sql).result().to_dataframe(create_bqstorage_client=False)


@st.cache_data(ttl=60, show_spinner=False)
def get_sensor_readings(limit: int = 500) -> pd.DataFrame:
    sql = f"""
        SELECT filename, event_time, temperature, humidity, soil_moisture, ingested_at
        FROM `{PROJECT_ID}.{DATASET}.sensor_readings`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = _query(sql)
    if not df.empty:
        df["event_time"] = _to_naive_utc(df["event_time"])
    return df


def _to_naive_utc(series: pd.Series) -> pd.Series:
    """Convert a datetime series to tz-naive UTC.

    BigQuery TIMESTAMP columns come back as tz-aware (UTC). The dashboard mixes
    them with naive datetimes from datetime.utcnow(), so we strip the tz here
    to keep arithmetic consistent.
    """
    s = pd.to_datetime(series, errors="coerce", utc=True)
    return s.dt.tz_convert(None) if s.dt.tz is not None else s


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Strip '%' / units and coerce to float, leaving non-parseable values as NaN."""
    if series.dtype.kind in "fiu":
        return series.astype(float)
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None, "None": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


@st.cache_data(ttl=60, show_spinner=False)
def get_plant_health(limit: int = 50) -> pd.DataFrame:
    sql = f"""
        SELECT
            filename, event_time, plant_type, health_status, confidence,
            severity, summary, possible_issues, recommendations,
            temperature, humidity, soil_moisture, ingested_at
        FROM `{PROJECT_ID}.{DATASET}.plant_health`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = _query(sql)
    if not df.empty:
        df["event_time"] = _to_naive_utc(df["event_time"])
        for col in ("confidence", "severity", "temperature", "humidity", "soil_moisture"):
            if col in df.columns:
                df[col] = _coerce_numeric(df[col])
    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_weather_forecast(limit: int = 200) -> pd.DataFrame:
    sql = f"""
        SELECT
            adm4, kotkab, kecamatan, desa, datetime_utc, datetime_local,
            temperature, humidity, precipitation_mm, wind_speed,
            weather_code, weather_desc, weather_desc_en
        FROM `{PROJECT_ID}.{DATASET}.weather_forecast`
        ORDER BY datetime_utc ASC
        LIMIT {int(limit)}
    """
    df = _query(sql)
    if not df.empty:
        df["datetime_utc"] = _to_naive_utc(df["datetime_utc"])
        df["datetime_local"] = _to_naive_utc(df["datetime_local"])
    return df


def parse_json_list(value) -> list[str]:
    """possible_issues / recommendations are stored as JSON-encoded strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return [str(parsed)]
    except json.JSONDecodeError:
        return [text]
