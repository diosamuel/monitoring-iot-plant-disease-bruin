from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import parseJsonList
from models import Metrics, VisionInsight
from utils import (
    computeMetrics,
    computeVision,
    fmtVal,
    loadPlantHealth,
    loadSensorReadings,
    loadWeather,
    parsePixelPoints,
    precipNote,
    renderHeatmapOverlay,
    utcNow,
    weatherIcon,
)


class PlainDashboard:

    def __init__(self, imageDir: Optional[Path] = None):
        self.imageDir: Path = imageDir or Path(
            os.getenv(
                "PLANT_IMAGE_DIR",
                str(Path(__file__).resolve().parents[1] / "api" / "images"),
            )
        )
        self.sensorDf: pd.DataFrame = pd.DataFrame()
        self.healthDf: pd.DataFrame = pd.DataFrame()
        self.weatherDf: pd.DataFrame = pd.DataFrame()
        self.metrics: Metrics = Metrics()
        self.vision: VisionInsight = VisionInsight()
        self.heatmapPoints: list[tuple[float, float]] = []

    @staticmethod
    def safeLoad(loader, label: str):
        try:
            return loader()
        except Exception as exc:
            st.warning(f"{label} unavailable: {exc}")
            return pd.DataFrame()

    def loadData(self):
        self.sensorDf = self.safeLoad(lambda: loadSensorReadings(500), "Sensor data")
        self.healthDf = self.safeLoad(lambda: loadPlantHealth(50), "Plant health data")
        self.weatherDf = self.safeLoad(lambda: loadWeather(200), "Weather data")
        self.metrics = computeMetrics(self.sensorDf, self.healthDf)
        self.vision, self.heatmapPoints = computeVision(self.healthDf, parseJsonList)

    def renderHeader(self):
        st.title("🌱 Smart Plant Monitoring System")
        st.caption("Live telemetry, vision analysis and forecast")
        st.divider()

    def renderTopRow(self):
        imgCol, metricsCol = st.columns([1, 2], gap="medium")
        with imgCol:
            self.renderImageCard()
        with metricsCol:
            self.renderMetrics()
            st.divider()
            self.renderTrendsCard()

    def renderImageCard(self):
        st.subheader("📷 Latest Capture")
        v = self.vision

        # Resolve image path
        candidatePath: Optional[Path] = None
        if v.available and v.filename:
            p = self.imageDir / v.filename
            if p.exists():
                candidatePath = p
        if candidatePath is None and self.imageDir.exists():
            jpgs = sorted(self.imageDir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
            if jpgs:
                candidatePath = jpgs[0]

        # Build caption
        ts = v.eventTime.strftime("%Y-%m-%d %H:%M:%S") if v.eventTime is not None else ""
        caption = f"ESP32-CAM • {ts}".rstrip(" •") if ts else f"ESP32-CAM • {candidatePath.name if candidatePath else ''}"

        # Render image (with optional heatmap overlay)
        if candidatePath is not None:
            if self.heatmapPoints:
                overlay = renderHeatmapOverlay(candidatePath, self.heatmapPoints)
                if overlay is not None:
                    st.image(overlay, caption=f"{caption} • heatmap", use_container_width=True)
                else:
                    st.image(str(candidatePath), caption=caption, use_container_width=True)
            else:
                st.image(str(candidatePath), caption=caption, use_container_width=True)
        else:
            st.info("No image available")

        if v.available:
            st.write(f"**Status:** {'✅ Healthy' if v.isHealthy else '⚠️ Warning'}")
            st.write(f"**{v.title}**")
            if self.heatmapPoints:
                st.caption(f"Heatmap: {len(self.heatmapPoints)} points overlaid")

    def renderMetrics(self):
        m = self.metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🌡️ Temperature", fmtVal(m.temperature, ".1f", "°C"))
        with c2:
            st.metric("💧 Air Humidity", fmtVal(m.humidity, ".0f", "%"))
        with c3:
            st.metric("🌱 Soil Moisture", fmtVal(m.soilPct, "d", "%") if m.soilPct is not None else "--")
        with c4:
            if self.weatherDf.empty:
                st.metric("☁️ Weather", "--")
                return
            nowUtc = pd.Timestamp(utcNow())
            wdf = self.weatherDf.copy()
            wdf["_delta"] = (wdf["datetime_utc"] - nowUtc).abs()
            cur = wdf.sort_values("_delta").iloc[0]
            desc = str(cur.get("weather_desc_en") or cur.get("weather_desc") or "")
            city = str(cur.get("kotkab") or "")
            st.metric(
                label=f"{weatherIcon(desc)} Weather — {city}",
                value=fmtVal(cur.get("temperature"), ".0f", "°C"),
                help=desc or "BMKG forecast",
            )
            note = precipNote(wdf, nowUtc)
            if note:
                st.caption(note)

    def renderTrendsCard(self):
        view = st.radio(
            "Series", ["Temperature", "Humidity"],
            horizontal=True, label_visibility="collapsed", key="sensor_view",
        )
        if self.sensorDf.empty:
            st.info("No sensor readings available yet.")
            return

        cutoff = self.sensorDf["event_time"].max() - timedelta(hours=24)
        last24 = self.sensorDf[self.sensorDf["event_time"] >= cutoff].sort_values("event_time")
        if last24.empty:
            last24 = self.sensorDf.sort_values("event_time").tail(50)

        isTemp = view == "Temperature"
        series   = last24["temperature"] if isTemp else last24["humidity"]
        yUnit    = "°C" if isTemp else "%"
        color    = "#DC2626" if isTemp else "#2563EB"
        fillColor = "rgba(220,38,38,0.10)" if isTemp else "rgba(37,99,235,0.10)"

        fig = go.Figure(go.Scatter(
            x=last24["event_time"], y=series, mode="lines",
            line=dict(color=color, width=3, shape="spline", smoothing=0.8),
            fill="tozeroy", fillcolor=fillColor,
            hovertemplate=f"%{{x|%H:%M}}<br>%{{y:.1f}}{yUnit}<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10), height=240,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, ticksuffix=f" {yUnit}"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    def renderVisionDetails(self):
        v = self.vision
        st.subheader("🤖 Gemini Vision Analysis")
        if not v.available:
            st.info("No vision analysis available yet.")
            return

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Confidence", f"{v.confidencePct}%")
        with c2:
            st.metric("Severity", fmtVal(v.severity, ".0f", "%", "n/a"))

        st.write(f"**Summary:** {v.summary}")
        if v.recommendations:
            with st.expander("Recommendations", expanded=True):
                for rec in v.recommendations[:3]:
                    st.write(f"- {rec[:140]}")
        if self.heatmapPoints:
            st.caption(f"Heatmap: {len(self.heatmapPoints)} pixel points overlaid on capture.")

        st.subheader("💡 AI Actions")
        severity = v.severity or 0.0
        priority = "🔴 High" if severity >= 50 else "🟡 Med" if severity >= 20 else "🟢 Low"

        actions: list[tuple[str, str, str]] = []
        if v.recommendations:
            actions.append((v.recommendations[0][:60], "From vision analysis", priority))
        if self.metrics.soilRaw is not None and self.metrics.soilRaw > 600:
            actions.append(("Increase Irrigation", "Soil moisture low", "🟡 Med"))
        for rec in v.recommendations[1:3]:
            actions.append((rec[:60], "Recommendation", "🟢 Low"))

        if actions:
            for text, sub, prio in actions:
                st.write(f"{prio} — {text}")
                st.caption(sub)
        else:
            st.write("No actions required.")

    def run(self):
        st.set_page_config(
            page_title="Smart Plant Monitoring",
            page_icon="🌱",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        self.renderHeader()
        self.loadData()
        self.renderTopRow()
        st.divider()
        self.renderVisionDetails()
