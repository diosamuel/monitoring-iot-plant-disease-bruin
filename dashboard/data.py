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
def bqClient() -> bigquery.Client:
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=creds)


def runQuery(sql: str) -> pd.DataFrame:
    return bqClient().query(sql).result().to_dataframe(create_bqstorage_client=False)


def toNaiveUtc(series: pd.Series) -> pd.Series:
    """Convert a datetime series to tz-naive UTC."""
    s = pd.to_datetime(series, errors="coerce", utc=True)
    return s.dt.tz_convert(None) if s.dt.tz is not None else s


def coerceNumeric(series: pd.Series) -> pd.Series:
    """Strip percent signs / units and coerce to float, NaN on failure."""
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
def getSensorReadings(limit: int = 500) -> pd.DataFrame:
    sql = f"""
        SELECT filename, event_time, temperature, humidity, soil_moisture, ingested_at
        FROM `{PROJECT_ID}.{DATASET}.sensor_readings`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["event_time"] = toNaiveUtc(df["event_time"])
    return df


@st.cache_data(ttl=60, show_spinner=False)
def getPlantHealth(limit: int = 50) -> pd.DataFrame:
    sql = f"""
        SELECT
            filename, event_time, plant_type, health_status, confidence,
            severity, summary, possible_issues, recommendations,
            temperature, humidity, soil_moisture, ingested_at
        FROM `{PROJECT_ID}.{DATASET}.plant_health`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["event_time"] = toNaiveUtc(df["event_time"])
        for col in ("confidence", "severity", "temperature", "humidity", "soil_moisture"):
            if col in df.columns:
                df[col] = coerceNumeric(df[col])
    return df


@st.cache_data(ttl=300, show_spinner=False)
def getWeatherForecast(limit: int = 200) -> pd.DataFrame:
    sql = f"""
        SELECT
            adm4, kotkab, kecamatan, desa, datetime_utc, datetime_local,
            temperature, humidity, precipitation_mm, wind_speed,
            weather_code, weather_desc, weather_desc_en
        FROM `{PROJECT_ID}.{DATASET}.weather_forecast`
        ORDER BY datetime_utc ASC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["datetime_utc"] = toNaiveUtc(df["datetime_utc"])
        df["datetime_local"] = toNaiveUtc(df["datetime_local"])
    return df


def parseJsonList(value) -> list[str]:
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
