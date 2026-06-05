from __future__ import annotations

import base64
import io
import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image


# ---------------------------------------------------------------------------
# BigQuery configuration
# ---------------------------------------------------------------------------

PROJECT_ID = os.getenv("BQ_PROJECT_ID", "learngcp-461809")
GOLD_DATASET = os.getenv("BQ_GOLD_DATASET", "gold")
SILVER_DATASET = os.getenv("BQ_SILVER_DATASET", "silver")
SERVICE_ACCOUNT_FILE = os.getenv(
    "GCP_SERVICE_ACCOUNT_FILE",
    str(Path(__file__).resolve().parents[1] / "secrets" / "gcp-secrets.json"),
)


@lru_cache(maxsize=1)
def bqClient():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=creds)


def runQuery(sql: str):
    return bqClient().query(sql).result().to_dataframe(create_bqstorage_client=False)


# ---------------------------------------------------------------------------
# Data-frame helpers
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


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner="Loading sensor data...")
def loadSensorReadings(limit: int = 500):
    sql = f"""
        SELECT filename, event_time, temperature, humidity, soil_moisture
        FROM `{PROJECT_ID}.{SILVER_DATASET}.sensor`
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


@st.cache_data(ttl=60, show_spinner="Loading plant health...")
def loadPlantHealth(limit: int = 50):
    sql = f"""
        SELECT
            filename, event_time, plant_type, health_status, confidence,
            severity, summary, possible_issues, recommendations, heatmap,
            avg_temperature, avg_humidity, avg_soil_moisture
        FROM `{PROJECT_ID}.{GOLD_DATASET}.plant_health`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["event_time"] = toNaiveUtc(df["event_time"])
        for col in ("confidence", "severity", "avg_temperature", "avg_humidity", "avg_soil_moisture"):
            if col in df.columns:
                df[col] = coerceNumeric(df[col])
    return df


@st.cache_data(ttl=300, show_spinner="Loading weather...")
def loadWeather(limit: int = 200):
    sql = f"""
        SELECT *
        FROM `{PROJECT_ID}.{SILVER_DATASET}.weather`
        ORDER BY datetime_utc ASC
        LIMIT {int(limit)}
    """
    df = runQuery(sql)
    if not df.empty:
        df["datetime_utc"] = toNaiveUtc(df["datetime_utc"])
        if "datetime_local" in df.columns:
            df["datetime_local"] = toNaiveUtc(df["datetime_local"])
        for col in ("adm4", "kotkab", "kecamatan", "desa", "weather_desc", "weather_desc_en"):
            if col in df.columns:
                df[col] = df[col].astype(str).replace("None", "")
        for col in ("temperature", "humidity", "precipitation_mm", "wind_speed"):
            if col in df.columns:
                df[col] = coerceNumeric(df[col])
    return df


def utcNow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def latestValue(series: pd.Series, default: Optional[float] = None):
    if series is None or series.empty:
        return default
    val = series.iloc[0]
    if pd.isna(val):
        return default
    return float(val)


def percentOfRange(value: Optional[float], lo: float, hi: float):
    if value is None or hi == lo:
        return 0
    pct = (value - lo) / (hi - lo) * 100
    return int(max(0, min(100, pct)))


def fmtVal(value: Optional[float], fmt: str, unit: str = "", fallback: str = "--") -> str:
    """Format a nullable float with unit, or return fallback."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    return f"{value:{fmt}} {unit}".strip()


def weatherIcon(desc: str) -> str:
    d = desc.lower()
    if "rain" in d or "hujan" in d:
        return "🌧️"
    if "cloud" in d or "berawan" in d:
        return "⛅"
    if "clear" in d or "cerah" in d:
        return "☀️"
    return "🌤️"


def precipNote(wdf: pd.DataFrame, nowUtc: pd.Timestamp) -> str:
    """Return a short rain forecast caption from the next 3 weather rows."""
    upcoming = wdf[wdf["datetime_utc"] >= nowUtc].head(3)
    if upcoming.empty:
        return ""
    nextRain = upcoming[upcoming["precipitation_mm"].fillna(0) > 0]
    if not nextRain.empty:
        mins = max(0, int((nextRain.iloc[0]["datetime_utc"] - nowUtc).total_seconds() // 60))
        return f"⏱️ Rain in ~{mins} min"
    return "☀️ No rain expected"


def imageDataUri(path: Path):
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "plant_heat",
    [
        (0.0, (0.0, 0.0, 0.0, 0.0)),
        (0.3, (1.0, 0.85, 0.0, 0.45)),
        (0.7, (1.0, 0.45, 0.0, 0.7)),
        (1.0, (0.85, 0.0, 0.0, 0.9)),
    ],
)


def parsePixelPoints(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = value if isinstance(value, str) else str(value)
    text = text.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    points: list[tuple[float, float]] = []
    if isinstance(parsed, list):
        for entry in parsed:
            if (
                isinstance(entry, (list, tuple))
                and len(entry) >= 2
                and all(isinstance(v, (int, float)) for v in entry[:2])
            ):
                points.append((float(entry[0]), float(entry[1])))
    return points


def gaussianDensity(width: int, height: int, points: Iterable[tuple[float, float]], sigma: float):
    grid = np.zeros((height, width), dtype=np.float32)
    pts = [(x, y) for x, y in points if 0 <= x < width and 0 <= y < height]
    if not pts:
        return grid
    radius = int(np.ceil(3.0 * sigma))
    for x, y in pts:
        x0 = max(0, int(x) - radius)
        x1 = min(width, int(x) + radius + 1)
        y0 = max(0, int(y) - radius)
        y1 = min(height, int(y) + radius + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = np.arange(x0, x1, dtype=np.float32)
        ys = np.arange(y0, y1, dtype=np.float32)
        xx, yy = np.meshgrid(xs, ys)
        d2 = (xx - x) ** 2 + (yy - y) ** 2
        grid[y0:y1, x0:x1] += np.exp(-d2 / (2.0 * sigma * sigma))
    peak = grid.max()
    if peak > 0:
        grid /= peak
    return grid


def renderHeatmapOverlay(imagePath: Path, points: list[tuple[float, float]]):
    try:
        img = Image.open(imagePath).convert("RGB")
    except (FileNotFoundError, OSError):
        return None

    width, height = img.size
    sigma = max(20.0, min(width, height) * 0.06)
    density = gaussianDensity(width, height, points, sigma=sigma)

    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(np.asarray(img))
    if density.any():
        ax.imshow(
            density,
            cmap=HEATMAP_CMAP,
            vmin=0.0,
            vmax=1.0,
            interpolation="bilinear",
        )
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.scatter(xs, ys, s=40, facecolors="none", edgecolors="white", linewidths=1.5)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Domain computations (pure: dataframe → model)
# ---------------------------------------------------------------------------

def computeMetrics(sensorDf: pd.DataFrame, healthDf: pd.DataFrame):
    from models import Metrics  # local import to avoid circular deps

    m = Metrics()
    for attr, col in (("temperature", "temperature"), ("humidity", "humidity"), ("soilRaw", "soil_moisture")):
        if col in sensorDf:
            setattr(m, attr, latestValue(sensorDf[col]))
    if m.soilRaw is not None:
        m.soilPct = max(0, min(100, int(round(100 - (m.soilRaw / 1023.0) * 100))))

    if not healthDf.empty:
        total = len(healthDf)
        unhealthy = int((healthDf["health_status"] != "healthy").sum())
        m.unhealthyPct = unhealthy / total * 100.0
        avgSev = float(healthDf["severity"].fillna(0).mean())
        avgConf = float(healthDf["confidence"].fillna(0).mean()) * 100.0
        m.healthScore = max(0, min(100, int(round(
            100 - m.unhealthyPct - avgSev * 0.5 + (avgConf - 50) * 0.1
        ))))
    return m


def computeVision(healthDf: pd.DataFrame, parseJsonListFn):
    from models import VisionInsight  # local import to avoid circular deps

    v = VisionInsight()
    heatmapPoints: list[tuple[float, float]] = []
    if healthDf.empty:
        return v, heatmapPoints

    latest = healthDf.iloc[0]
    v.available = True
    v.filename = str(latest.get("filename") or "")
    v.eventTime = pd.to_datetime(latest.get("event_time"))
    v.status = str(latest.get("health_status") or "unknown").lower()
    v.isHealthy = v.status == "healthy"
    v.badge = "OK" if v.isHealthy else "WARNING"
    v.issues = parseJsonListFn(latest.get("possible_issues"))
    v.recommendations = parseJsonListFn(latest.get("recommendations"))
    v.title = (
        "Healthy Canopy" if v.isHealthy
        else "Disease Detected" if v.status == "diseased"
        else "Inspection Needed"
    )
    if v.issues:
        v.title = v.issues[0][:60]

    conf = float(latest.get("confidence") or 0.0)
    v.confidencePct = int(round(conf * 100)) if conf <= 1 else int(round(conf))
    severity = latest.get("severity")
    v.severity = float(severity) if severity is not None and not pd.isna(severity) else None
    v.summary = str(latest.get("summary") or "No summary available.")

    if "heatmap" in healthDf.columns:
        heatmapPoints = parsePixelPoints(latest.get("heatmap"))
    return v, heatmapPoints
