from __future__ import annotations
import io
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
import pandas as pd
import streamlit as st
from google.cloud import bigquery, storage
from google.oauth2 import service_account

PROJECT_ID = os.getenv("BQ_PROJECT_ID")
DATASET_GOLD = os.getenv("BQ_DATASET_GOLD")
GCS_BUCKET = os.getenv("GCS_BUCKET")
SERVICE_ACCOUNT_FILE = os.getenv("GCP_SERVICE_ACCOUNT_FILE")


@lru_cache(maxsize=1)
def _credentials():
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


@lru_cache(maxsize=1)
def bqClient():
    return bigquery.Client(project=PROJECT_ID, credentials=_credentials())


@lru_cache(maxsize=1)
def gcsClient():
    return storage.Client(credentials=_credentials())


def runQuery(sql: str):
    return bqClient().query(sql).result().to_dataframe(create_bqstorage_client=False)


def getLatestImageBytes(filename: str):
    """Download image bytes from GCS. Returns None if bucket is unconfigured or blob missing."""
    if not GCS_BUCKET:
        return None
    try:
        bucket = gcsClient().bucket(GCS_BUCKET)
        blob = bucket.blob(filename)
        buf = io.BytesIO()
        blob.download_to_file(buf)
        return buf.getvalue()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Dataframe helpers
# ---------------------------------------------------------------------------

def toNaiveUtc(series: pd.Series):
    s = pd.to_datetime(series, errors="coerce", utc=True)
    return s.dt.tz_convert(None) if s.dt.tz is not None else s


def coerceNumeric(series: pd.Series):
    if series.dtype.kind in "fiu":
        return series.astype(float)
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None, "None": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def latestValue(series: pd.Series, default: Optional[float] = None):
    if series is None or series.empty:
        return default
    val = series.iloc[0]
    if pd.isna(val):
        return default
    return float(val)


def parseJsonList(value):
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


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def getSensorReadings(limit: int = 500):
    sql = f"""
        SELECT filename, event_time, temperature, humidity, soil_moisture, ingested_at
        FROM `{PROJECT_ID}.{DATASET_GOLD}.sensor_readings`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["event_time"] = toNaiveUtc(df["event_time"])
        for col in ("temperature", "humidity", "soil_moisture"):
            if col in df.columns:
                df[col] = coerceNumeric(df[col])
    return df


@st.cache_data(ttl=60, show_spinner=False)
def getPlantHealth(limit: int = 50):
    sql = f"""
        SELECT
            filename, event_time, health_status, confidence,
            severity, summary, possible_issues, recommendations,
            temperature, humidity, soil_moisture, ingested_at
        FROM `{PROJECT_ID}.{DATASET_GOLD}.plant_health`
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
def getWeatherForecast(limit: int = 200):
    sql = f"""
        SELECT
            adm4, kotkab, kecamatan, desa, datetime_utc, datetime_local,
            temperature, humidity, precipitation_mm, wind_speed,
            weather_code, weather_desc, weather_desc_en
        FROM `{PROJECT_ID}.{DATASET_GOLD}.weather_forecast`
        ORDER BY datetime_utc ASC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["datetime_utc"] = toNaiveUtc(df["datetime_utc"])
        df["datetime_local"] = toNaiveUtc(df["datetime_local"])
    return df
