from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data import getSensorReadings, getPlantHealth, getWeatherForecast, getLatestImageBytes, latestValue, parseJsonList


@dataclass
class Metrics:
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soilRaw: Optional[float] = None
    soilPct: Optional[int] = None
    healthScore: int = 0
    unhealthyPct: float = 0.0


@dataclass
class VisionInsight:
    available: bool = False
    filename: str = ""
    eventTime: Optional[pd.Timestamp] = None
    status: str = "unknown"
    isHealthy: bool = False
    badge: str = "WARNING"
    title: str = "Inspection Needed"
    confidencePct: int = 0
    severity: Optional[float] = None
    summary: str = "No summary available."
    recommendations: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


# Utility functions (formerly from utils.py)

def fmtVal(value: Optional[float], fmt: str, unit: str = "", fallback: str = "--") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    return f"{value:{fmt}} {unit}".strip()

def precipNote(wdf: pd.DataFrame, nowUtc: pd.Timestamp) -> str:
    upcoming = wdf[wdf["datetime_utc"] >= nowUtc].head(3)
    if upcoming.empty:
        return ""
    nextRain = upcoming[upcoming["precipitation_mm"].fillna(0) > 0]
    if not nextRain.empty:
        mins = max(0, int((nextRain.iloc[0]["datetime_utc"] - nowUtc).total_seconds() // 60))
        return f"Rain in ~{mins} min"
    return "No rain expected"


def computeMetrics(sensorDf: pd.DataFrame, healthDf: pd.DataFrame):
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


def computeVision(healthDf: pd.DataFrame):
    imageInsight = VisionInsight()
    if healthDf.empty:
        return imageInsight

    latest = healthDf.iloc[0]
    imageInsight.available = True
    imageInsight.filename = str(latest.get("filename") or "")
    imageInsight.eventTime = pd.to_datetime(latest.get("event_time"))
    imageInsight.status = str(latest.get("health_status") or "unknown").lower()
    imageInsight.isHealthy = imageInsight.status == "healthy"
    imageInsight.badge = "OK" if imageInsight.isHealthy else "WARNING"
    imageInsight.issues = parseJsonList(latest.get("possible_issues"))
    imageInsight.recommendations = parseJsonList(latest.get("recommendations"))
    imageInsight.title = (
        "Healthy Leaf" if imageInsight.isHealthy
        else "Disease Detected" if imageInsight.status == "diseased"
        else "Inspection Needed"
    )
    if imageInsight.issues:
        imageInsight.title = imageInsight.issues[0][:60]

    conf = float(latest.get("confidence") or 0.0)
    imageInsight.confidencePct = int(round(conf * 100)) if conf <= 1 else int(round(conf))
    severity = latest.get("severity")
    imageInsight.severity = float(severity) if severity is not None and not pd.isna(severity) else None
    imageInsight.summary = str(latest.get("summary") or "No summary available.")
    return imageInsight


class Dashboard:
    def __init__(self):
        self.sensorDf = pd.DataFrame()
        self.healthDf = pd.DataFrame()
        self.weatherDf = pd.DataFrame()
        self.metrics = Metrics()
        self.vision = VisionInsight()

    def loadData(self):
        self.sensorDf = getSensorReadings(500)
        self.healthDf = getPlantHealth(50)
        self.weatherDf = getWeatherForecast(200)
        self.metrics = computeMetrics(self.sensorDf, self.healthDf)
        self.vision = computeVision(self.healthDf)

    def renderHeader(self):
        st.title(" Smart Plant Monitoring System")
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
        st.subheader("Latest Capture")
        v = self.vision

        ts = v.eventTime.strftime("%Y-%m-%d %H:%M:%S") if v.eventTime is not None else ""
        caption = f"ESP32-CAM • {ts}" if ts else "ESP32-CAM"

        img_bytes = None
        if v.available and v.filename:
            img_bytes = getLatestImageBytes(v.filename)

        if img_bytes is not None:
            st.image(img_bytes, caption=caption, use_container_width=True)
        else:
            # fallback
            st.image("https://placehold.co/600x400", caption=caption, use_container_width=True)

        if v.available:
            st.write(f"**Status:** {'Healthy' if v.isHealthy else 'Warning'}")
            st.write(f"**{v.title}**")

    def renderMetrics(self):
        m = self.metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Temperature", fmtVal(m.temperature, ".1f", "°C"))
        with c2:
            st.metric(" Air Humidity", fmtVal(m.humidity, ".0f", "%"))
        with c3:
            st.metric(" Soil Moisture", fmtVal(m.soilPct, "d", "%") if m.soilPct is not None else "--")
        with c4:
            if self.weatherDf.empty:
                st.metric(" Weather", "--")
                return
            nowUtc = pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
            wdf = self.weatherDf.copy()
            wdf["_delta"] = (wdf["datetime_utc"] - nowUtc).abs()
            cur = wdf.sort_values("_delta").iloc[0]
            desc = str(cur.get("weather_desc_en") or cur.get("weather_desc") or "")
            city = str(cur.get("kotkab") or "")
            st.metric(
                label=f"Weather {city}",
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
        series = last24["temperature"] if isTemp else last24["humidity"]
        yUnit = "°C" if isTemp else "%"
        color = "#DC2626" if isTemp else "#2563EB"
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
        st.subheader(" Gemini Vision Analysis")
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

        st.subheader(" AI Actions")
        severity = v.severity or 0.0
        priority = " High" if severity >= 50 else " Med" if severity >= 20 else " Low"

        actions= []
        if v.recommendations:
            actions.append((v.recommendations[0][:60], "From vision analysis", priority))
        if self.metrics.soilRaw is not None and self.metrics.soilRaw > 600:
            actions.append(("Increase Irrigation", "Soil moisture low", " Med"))
        for rec in v.recommendations[1:3]:
            actions.append((rec[:60], "Recommendation", " Low"))

        if actions:
            for text, sub, prio in actions:
                st.write(f"{prio} — {text}")
                st.caption(sub)
        else:
            st.write("No actions required.")

    def run(self):
        st.set_page_config(
            page_title="Smart Plant Monitoring",
            page_icon="",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        self.renderHeader()
        self.loadData()
        self.renderTopRow()
        st.divider()
        self.renderVisionDetails()
