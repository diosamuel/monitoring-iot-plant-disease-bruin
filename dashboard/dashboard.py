"""Dashboard class for the Smart Plant Monitoring System."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import (
    getPlantHealth,
    getSensorReadings,
    getWeatherForecast,
    parseJsonList,
)
from models import Metrics, VisionInsight
from styles import injectStyles
from utils import imageDataUri, latestValue, percentOfRange, utcNow


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

    
    @staticmethod
    @st.cache_data(ttl=60, show_spinner="Loading sensor data...")
    def _loadSensor() -> pd.DataFrame:
        try:
            return getSensorReadings(500)
        except Exception as exc:
            st.warning(f"Sensor data unavailable: {exc}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=60, show_spinner="Loading plant health...")
    def _loadHealth() -> pd.DataFrame:
        try:
            return getPlantHealth(50)
        except Exception as exc:
            st.warning(f"Plant health data unavailable: {exc}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=300, show_spinner="Loading weather...")
    def _loadWeather() -> pd.DataFrame:
        try:
            return getWeatherForecast(200)
        except Exception as exc:
            st.warning(f"Weather data unavailable: {exc}")
            return pd.DataFrame()

    def loadData(self):
        self.sensorDf = self._loadSensor()
        self.healthDf = self._loadHealth()
        self.weatherDf = self._loadWeather()
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

    
    def _resolveLeafImage(self) -> tuple[Optional[str], str]:
        """Return (data_uri, caption). Caller decides how to render."""
        if self.vision.available and self.vision.filename:
            candidate = self.imageDir / self.vision.filename
            ts = (
                self.vision.eventTime.strftime("%Y-%m-%d %H:%M:%S")
                if self.vision.eventTime is not None
                else ""
            )
            if candidate.exists():
                return imageDataUri(candidate), f"ESP32-CAM • {ts}".rstrip(" •")
        if self.imageDir.exists():
            jpgs = sorted(
                self.imageDir.glob("*.jpg"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if jpgs:
                return imageDataUri(jpgs[0]), f"ESP32-CAM • {jpgs[0].name}"
        return None, "ESP32-CAM"

    
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
            # ✅ Native columns — no CSS grid, no sanitizer interference
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
            alertHtml = f"""
              <div class="sp-alert {alertClass}" style="margin-top:12px;">
                <div class="row">
                  <div>Status Alert</div>
                  <div class="pill">{v.badge}</div>
                </div>
                <div class="title">{v.title}</div>
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
        else:
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
        self.renderSidebar()
        self.renderHeader()
        self.loadData()
        self.renderInsightsBanner()
        self.renderTopRow()
        self.renderDetailRow()
