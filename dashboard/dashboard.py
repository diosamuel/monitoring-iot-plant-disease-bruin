"""Dashboard class for the Smart Plant Monitoring System.

Schemas changed in May 2026 — the dashboard now reads directly from the
new gold/silver tables and bypasses the legacy `data.py` helpers:

- `gold.sensor_readings`   (aggregated per filename: avg/min/max)
- `gold.plant_health`      (image predictions + aggregated sensor envelope)
- `gold.weather_forecast`  (daily aggregated weather)
- `silver.sensor`          (per-row sensor readings, used for time-series)
- `silver.weather`          (per-interval weather, used for "rain in N min")
- `raw.image_analytics`    (carries the `pixel`/`heatmap` JSON from Gemini)

If the latest plant_health row exposes a `heatmap`/`pixel` array, the
dashboard renders a matplotlib heatmap overlay on top of the leaf image.
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from google.cloud import bigquery
from google.oauth2 import service_account

from data import parseJsonList
from models import Metrics, VisionInsight
from styles import injectStyles
from utils import imageDataUri, latestValue, parsePixelPoints, percentOfRange, renderHeatmapOverlay, utcNow


PROJECT_ID = os.getenv("BQ_PROJECT_ID", "learngcp-461809")
GOLD_DATASET = os.getenv("BQ_GOLD_DATASET", "gold")
SILVER_DATASET = os.getenv("BQ_SILVER_DATASET", "silver")
SERVICE_ACCOUNT_FILE = os.getenv(
    "GCP_SERVICE_ACCOUNT_FILE",
    str(Path(__file__).resolve().parents[1] / "secrets" / "gcp-secrets.json"),
)


# ───────────────────────────── BigQuery helpers ──────────────────────────────

@lru_cache(maxsize=1)
def _bqClient() -> bigquery.Client:
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=creds)


def _runQuery(sql: str) -> pd.DataFrame:
    return _bqClient().query(sql).result().to_dataframe(create_bqstorage_client=False)


def _toNaiveUtc(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce", utc=True)
    return s.dt.tz_convert(None) if s.dt.tz is not None else s


def _coerceNumeric(series: pd.Series) -> pd.Series:
    if series.dtype.kind in "fiu":
        return series.astype(float)
    cleaned = (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None, "None": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


# ───────────────────────────── Data loaders ──────────────────────────────────

@st.cache_data(ttl=60, show_spinner="Loading sensor data...")
def _loadSensorReadings(limit: int = 500) -> pd.DataFrame:
    """Per-row sensor readings from `silver.sensor` for time-series trends."""
    sql = f"""
        SELECT
            filename,
            event_time,
            temperature,
            humidity,
            soil_moisture
        FROM `{PROJECT_ID}.{SILVER_DATASET}.sensor`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = _runQuery(sql)
    if not df.empty:
        df["event_time"] = _toNaiveUtc(df["event_time"])
        for col in ("temperature", "humidity", "soil_moisture"):
            if col in df.columns:
                df[col] = _coerceNumeric(df[col])
    return df


@st.cache_data(ttl=60, show_spinner="Loading plant health...")
def _loadPlantHealth(limit: int = 50) -> pd.DataFrame:
    """Image predictions joined with aggregated sensor envelope.

    Reads `gold.plant_health` directly. The `heatmap` column carries a
    JSON array of `[x, y]` pixel coordinates from Gemini Vision.
    """
    sql = f"""
        SELECT
            filename,
            event_time,
            plant_type,
            health_status,
            confidence,
            severity,
            summary,
            possible_issues,
            recommendations,
            heatmap,
            avg_temperature,
            avg_humidity,
            avg_soil_moisture
        FROM `{PROJECT_ID}.{GOLD_DATASET}.plant_health`
        ORDER BY event_time DESC
        LIMIT {int(limit)}
    """
    df = _runQuery(sql)
    if not df.empty:
        df["event_time"] = _toNaiveUtc(df["event_time"])
        for col in (
            "confidence",
            "severity",
            "avg_temperature",
            "avg_humidity",
            "avg_soil_moisture",
        ):
            if col in df.columns:
                df[col] = _coerceNumeric(df[col])
    return df


@st.cache_data(ttl=300, show_spinner="Loading weather...")
def _loadWeather(limit: int = 200) -> pd.DataFrame:
    """Per-interval weather from `silver.weather`."""
    sql = f"""
        SELECT *
        FROM `{PROJECT_ID}.{SILVER_DATASET}.weather`
        ORDER BY datetime_utc ASC
        LIMIT {int(limit)}
    """
    df = _runQuery(sql)
    if not df.empty:
        df["datetime_utc"] = _toNaiveUtc(df["datetime_utc"])
        if "datetime_local" in df.columns:
            df["datetime_local"] = _toNaiveUtc(df["datetime_local"])
        # Coerce string-typed columns that should be text
        for col in ("adm4", "kotkab", "kecamatan", "desa", "weather_desc", "weather_desc_en"):
            if col in df.columns:
                df[col] = df[col].astype(str).replace("None", "")
        # Coerce numeric columns
        for col in ("temperature", "humidity", "precipitation_mm", "wind_speed"):
            if col in df.columns:
                df[col] = _coerceNumeric(df[col])
    return df


# ───────────────────────────── Dashboard class ───────────────────────────────

class Dashboard:
    """Streamlit dashboard for the Smart Plant Monitoring System."""

    def __init__(self, imageDir: Optional[Path] = None):
        self.imageDir: Path = imageDir or Path(
            os.getenv(
                "PLANT_IMAGE_DIR",
                str(Path(__file__).resolve().parents[1] / "api" / "images"),
            )
        )
        # Data
        self.sensorDf: pd.DataFrame = pd.DataFrame()
        self.healthDf: pd.DataFrame = pd.DataFrame()
        self.weatherDf: pd.DataFrame = pd.DataFrame()
        # Derived
        self.metrics: Metrics = Metrics()
        self.vision: VisionInsight = VisionInsight()
        self.heatmapPoints: list[tuple[float, float]] = []

    @staticmethod
    def _safeLoad(loader, label: str) -> pd.DataFrame:
        try:
            return loader()
        except Exception as exc:
            st.warning(f"{label} unavailable: {exc}")
            return pd.DataFrame()

    def loadData(self):
        self.sensorDf = self._safeLoad(lambda: _loadSensorReadings(500), "Sensor data")
        self.healthDf = self._safeLoad(lambda: _loadPlantHealth(50), "Plant health data")
        self.weatherDf = self._safeLoad(lambda: _loadWeather(200), "Weather data")
        self._computeMetrics()
        self._computeVision()

    def _computeMetrics(self):
        m = Metrics()
        if "temperature" in self.sensorDf:
            m.temperature = latestValue(self.sensorDf["temperature"])
        if "humidity" in self.sensorDf:
            m.humidity = latestValue(self.sensorDf["humidity"])
        if "soil_moisture" in self.sensorDf:
            m.soilRaw = latestValue(self.sensorDf["soil_moisture"])
        if m.soilRaw is not None:
            m.soilPct = max(0, min(100, int(round(100 - (m.soilRaw / 1023.0) * 100))))

        if not self.healthDf.empty:
            total = len(self.healthDf)
            unhealthy = int((self.healthDf["health_status"] != "healthy").sum())
            m.unhealthyPct = unhealthy / total * 100.0
            avgSev = float(self.healthDf["severity"].fillna(0).mean())
            avgConf = float(self.healthDf["confidence"].fillna(0).mean()) * 100.0
            m.healthScore = max(
                0,
                min(
                    100,
                    int(round(100 - m.unhealthyPct - avgSev * 0.5 + (avgConf - 50) * 0.1)),
                ),
            )
        self.metrics = m

    def _computeVision(self):
        v = VisionInsight()
        self.heatmapPoints = []
        if self.healthDf.empty:
            self.vision = v
            return

        latest = self.healthDf.iloc[0]
        v.available = True
        v.filename = str(latest.get("filename") or "")
        v.eventTime = pd.to_datetime(latest.get("event_time"))
        v.status = str(latest.get("health_status") or "unknown").lower()
        v.isHealthy = v.status == "healthy"
        v.badge = "OK" if v.isHealthy else "WARNING"
        v.issues = parseJsonList(latest.get("possible_issues"))
        v.recommendations = parseJsonList(latest.get("recommendations"))

        if v.isHealthy:
            v.title = "Healthy Canopy"
        elif v.status == "diseased":
            v.title = "Disease Detected"
        else:
            v.title = "Inspection Needed"
        if v.issues:
            v.title = v.issues[0][:60]

        conf = float(latest.get("confidence") or 0.0)
        v.confidencePct = int(round(conf * 100)) if conf <= 1 else int(round(conf))

        severity = latest.get("severity")
        v.severity = (
            float(severity) if severity is not None and not pd.isna(severity) else None
        )
        v.summary = str(latest.get("summary") or "No summary available.")
        self.vision = v

        # Pixel/heatmap points (from gold.plant_health → heatmap column)
        if "heatmap" in self.healthDf.columns:
            self.heatmapPoints = parsePixelPoints(latest.get("heatmap"))

    def _resolveLeafImage(self) -> tuple[Optional[str], str]:
        """Return (data_uri, caption). Caller decides how to render."""
        candidatePath: Optional[Path] = None
        if self.vision.available and self.vision.filename:
            candidate = self.imageDir / self.vision.filename
            if candidate.exists():
                candidatePath = candidate
        if candidatePath is None and self.imageDir.exists():
            jpgs = sorted(
                self.imageDir.glob("*.jpg"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if jpgs:
                candidatePath = jpgs[0]

        if candidatePath is None:
            return None, "ESP32-CAM"

        ts = (
            self.vision.eventTime.strftime("%Y-%m-%d %H:%M:%S")
            if self.vision.eventTime is not None
            else ""
        )
        caption = f"ESP32-CAM • {ts}".rstrip(" •") if ts else f"ESP32-CAM • {candidatePath.name}"

        # If we have heatmap points, render the matplotlib overlay.
        if self.heatmapPoints:
            overlay = renderHeatmapOverlay(candidatePath, self.heatmapPoints)
            if overlay is not None:
                return overlay, f"{caption} • heatmap"

        return imageDataUri(candidatePath), caption

    def renderPageSetup(self):
        st.set_page_config(
            page_title="Smart Plant Monitoring",
            page_icon="🌱",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        injectStyles()

    def renderSidebar(self):
        with st.sidebar:
            st.markdown(
                """
                <div class="sp-brand">
                  <div class="name">🌱 Smart Plant</div>
                  <div class="ver">V2.4 MONITORING</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.radio(
                "nav",
                [
                    "📊 Overview",
                    "📈 Analytics",
                    "☁️ Weather",
                    "📷 Camera",
                    "🤖 AI Lab",
                    "⚙️ System Status",
                    "✨ Insights",
                ],
                label_visibility="collapsed",
            )
            st.write("")
            st.button("Export Data", width="stretch")
            st.markdown(
                """
                <div style="position:absolute; bottom:24px; left:18px; right:18px; color:#64748B; font-size:0.85rem;">
                  ⚙️ Settings<br/>❓ Support
                </div>
                """,
                unsafe_allow_html=True,
            )

    def renderHeader(self):
        st.markdown(
            """
            <div class="sp-header">
              <div>
                <h1>Smart Plant Monitoring System</h1>
                <div class="sub">Live telemetry, vision analysis and forecast</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def renderInsightsBanner(self):
        pass

    @staticmethod
    def _metricCard(
        flavor: str, icon: str, title: str, value: str, unit: str, pulse: str, fillPct: int
    ) -> str:
        return f"""
          <div class="sp-metric {flavor}">
            <div class="top">
              <div class="label"><span class="icon">{icon}</span>{title}</div>
              <div class="pulse">{pulse}</div>
            </div>
            <div>
              <div class="value-row">
                <span class="value">{value}</span>
                <span class="unit">{unit}</span>
              </div>
              <div class="sp-bar"><span style="width:{fillPct}%"></span></div>
            </div>
          </div>
        """

    def renderTopRow(self):
        imgCol, metricsCol = st.columns([1, 2], gap="medium")
        with imgCol:
            self._renderImageCard()
        with metricsCol:
            m = self.metrics
            c1, c2, c3, c4 = st.columns(4, gap="small")

            with c1:
                st.markdown(self._metricCard(
                    "temp", "🌡️", "Temperature",
                    f"{m.temperature:.1f}" if m.temperature is not None else "--",
                    "°C", "", percentOfRange(m.temperature, 0, 40),
                ), unsafe_allow_html=True)

            with c2:
                st.markdown(self._metricCard(
                    "hum", "💧", "Air Humidity",
                    f"{m.humidity:.0f}" if m.humidity is not None else "--",
                    "%", "", percentOfRange(m.humidity, 0, 100),
                ), unsafe_allow_html=True)

            with c3:
                st.markdown(self._metricCard(
                    "soil", "🌱", "Soil Moisture",
                    f"{m.soilPct}" if m.soilPct is not None else "--",
                    "%", "", m.soilPct or 0,
                ), unsafe_allow_html=True)

            with c4:
                st.markdown(self._buildWeatherCardHtml(), unsafe_allow_html=True)
            self.renderTrendsCard()

    def _renderImageCard(self):
        leafSrc, caption = self._resolveLeafImage()
        v = self.vision

        if leafSrc is not None:
            imgInner = f'<img src="{leafSrc}" alt="Latest plant capture" />'
        else:
            imgInner = (
                '<div style="display:flex;align-items:center;justify-content:center;'
                'height:100%;color:#94A3B8;font-size:0.85rem;">No image available</div>'
            )

        if v.available:
            alertClass = "ok" if v.isHealthy else ""
            heatPill = (
                f'<span class="pill" style="margin-left:6px; background:#FEF3C7; color:#92400E;">{len(self.heatmapPoints)} pts</span>'
                if self.heatmapPoints
                else ""
            )
            alertHtml = f"""
              <div class="sp-alert {alertClass}" style="margin-top:12px;">
                <div class="row">
                  <div>Status Alert</div>
                  <div class="pill">{v.badge}</div>
                </div>
                <div class="title">{v.title}{heatPill}</div>
              </div>
            """
        else:
            alertHtml = ""

        st.markdown(
            f"""
            <div class="sp-image">
              <div class="hd"><div>Latest Capture</div><div>Live</div></div>
              <div class="frame">
                <span class="dot">REC</span>
                {imgInner}
              </div>
              <div class="ts">{caption}</div>
              {alertHtml}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def renderTrendsCard(self):
        view = st.radio(
            "Series",
            options=["Temperature", "Humidity"],
            horizontal=True,
            label_visibility="collapsed",
            key="sensor_view",
        )

        if self.sensorDf.empty:
            st.info("No sensor readings available yet.")
            return

        cutoff = self.sensorDf["event_time"].max() - timedelta(hours=24)
        last24 = self.sensorDf[self.sensorDf["event_time"] >= cutoff].sort_values(
            "event_time"
        )
        if last24.empty:
            last24 = self.sensorDf.sort_values("event_time").tail(50)

        isTemp = view == "Temperature"
        series = last24["temperature"] if isTemp else last24["humidity"]
        yUnit = "°C" if isTemp else "%"
        color = "#DC2626" if isTemp else "#2563EB"
        fillColor = "rgba(220,38,38,0.10)" if isTemp else "rgba(37,99,235,0.10)"

        fig = go.Figure(
            data=go.Scatter(
                x=last24["event_time"],
                y=series,
                mode="lines",
                line=dict(color=color, width=3, shape="spline", smoothing=0.8),
                fill="tozeroy",
                fillcolor=fillColor,
                hovertemplate=f"%{{x|%H:%M}}<br>%{{y:.1f}}{yUnit}<extra></extra>",
            )
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=240,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#64748B", linecolor="#E5E7EB"),
            yaxis=dict(
                showgrid=True,
                gridcolor="#F1F5F9",
                color="#64748B",
                ticksuffix=f" {yUnit}",
            ),
            showlegend=False,
            hoverlabel=dict(bgcolor="#0F172A", font_color="#fff"),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    def renderVisionDetails(self):
        v = self.vision
        sevText = f"{v.severity:.0f}% severity" if v.severity is not None else "n/a"
        recsHtml = (
            "<ul style='margin:6px 0 0 18px; padding:0; color:#1F2937; font-size:0.9rem; line-height:1.55;'>"
            + "".join(f"<li>{r[:140]}</li>" for r in v.recommendations[:3])
            + "</ul>"
            if v.recommendations
            else "<div class='body'>None.</div>"
        )

        # Build AI Actions section
        actionParts: list[str] = [
            '<div style="margin-top:18px; border-top:1px solid #E5E7EB; padding-top:14px;">',
            '<div class="sp-card-title"><div class="t">💡 AI Actions</div></div>',
        ]

        soil = self.metrics.soilRaw

        if v.available:
            severity = v.severity or 0.0
            if severity >= 50:
                priority = "high"
            elif severity >= 20:
                priority = "med"
            else:
                priority = "low"

            action_count = 0

            if v.recommendations:
                actionParts.append(
                    self._actionRow(v.recommendations[0][:60], "From vision analysis", priority)
                )
                action_count += 1

            if soil is not None and soil > 600:
                actionParts.append(
                    self._actionRow("Increase Irrigation", "Soil moisture low", "med")
                )
                action_count += 1

            for rec in v.recommendations[1:3]:
                actionParts.append(self._actionRow(rec[:60], "Recommendation", "low"))
                action_count += 1

            if action_count == 0:
                actionParts.append(
                    '<div style="color:#94A3B8; font-size:0.85rem; margin-top:6px;">No actions required.</div>'
                )
        else:
            actionParts.append(
                '<div style="color:#94A3B8; font-size:0.85rem; margin-top:6px;">No recommendations yet.</div>'
            )

        actionParts.append("</div>")
        actionsHtml = "".join(actionParts)

        heatmapNote = (
            f'<div class="lbl">Heatmap</div>'
            f'<div class="body">{len(self.heatmapPoints)} pixel points overlaid on capture.</div>'
            if self.heatmapPoints
            else ""
        )

        st.markdown(
            f"""
            <br/>
            <div class="sp-card">
              <div class="sp-card-title">
                <div class="t">Gemini Vision Analysis</div>
              </div>
            <div class="sp-conf">
              <div class="lbl">Confidence Score</div>
              <div class="bar"><span style="width:{v.confidencePct}%"></span></div>
              <div class="pct">{v.confidencePct}%</div>
            </div>

            <div class="sp-summary">
              <div class="lbl">Severity</div>
              <div class="body">{sevText}</div>

              <div class="lbl">Summary</div>
              <div class="body">{v.summary}</div>

              <div class="lbl">Recommendations</div>
              {recsHtml}

              {heatmapNote}
            </div>

            {actionsHtml}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _buildWeatherCardHtml(self) -> str:
        """Return weather card HTML string for inline grid placement."""
        if self.weatherDf.empty:
            return """
              <div class="sp-card sp-weather">
                <div class="top">
                    <div>☁️ BMKG Weather</div>
                </div>
                <div class="now">
                  <div class="ic">🌤️</div>
                  <div><div class="desc">No forecast yet</div></div>
                </div>
              </div>
            """

        nowUtc = pd.Timestamp(utcNow())
        wdf = self.weatherDf.copy()
        wdf["abs_delta"] = (wdf["datetime_utc"] - nowUtc).abs()
        cur = wdf.sort_values("abs_delta").iloc[0]
        city = str(cur.get("kotkab") or "Unknown")
        temp = cur.get("temperature")
        desc = str(cur.get("weather_desc_en") or cur.get("weather_desc") or "")

        rainNote = ""
        precipSoon = wdf[wdf["datetime_utc"] >= nowUtc].head(3)
        if not precipSoon.empty:
            nextRain = precipSoon[precipSoon["precipitation_mm"].fillna(0) > 0]
            if not nextRain.empty:
                first = nextRain.iloc[0]
                mins = max(0, int((first["datetime_utc"] - nowUtc).total_seconds() // 60))
                rainNote = f"⏱️ Rain in ~{mins} min"
            else:
                rainNote = "☀️ No rain expected"

        descLow = desc.lower()
        if "rain" in descLow or "hujan" in descLow:
            icon = "🌧️"
        elif "cloud" in descLow or "berawan" in descLow:
            icon = "⛅"
        elif "clear" in descLow or "cerah" in descLow:
            icon = "☀️"
        else:
            icon = "🌤️"

        tempStr = f"{temp:.0f}°C" if temp is not None and not pd.isna(temp) else "--"
        return f"""
          <div class="sp-card sp-weather">
            <div class="top">
              <div>☁️ BMKG Weather</div>
              <div>{city}</div>
            </div>
            <div class="now">
              <div class="ic">{icon}</div>
              <div>
                <div class="t">{tempStr}</div>
                <div class="desc">{desc or 'Forecast'}</div>
              </div>
            </div>
            <div class="note">{rainNote or '&nbsp;'}</div>
          </div>
        """

    @staticmethod
    def _actionRow(title: str, sub: str, level: str) -> str:
        return (
            f'<div class="sp-action"><div class="text"><div class="t">{title}</div>'
            f'<div class="s">{sub}</div></div><div class="pill {level}">{level}</div></div>'
        )

    def renderDetailRow(self):
        """Vision details full width."""
        self.renderVisionDetails()

    def run(self):
        self.renderPageSetup()
        # self.renderSidebar()
        self.renderHeader()
        self.loadData()
        self.renderInsightsBanner()
        self.renderTopRow()
        self.renderDetailRow()
