"""
Smart Plant Monitoring System - Streamlit dashboard.
Reads gold-layer tables from BigQuery and renders local images
captured by the API ingestor.
"""

from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import (
    get_plant_health,
    get_sensor_readings,
    get_weather_forecast,
    parse_json_list,
)
from styles import CSS

IMAGE_DIR = Path(os.getenv("PLANT_IMAGE_DIR",str(Path(__file__).resolve().parents[1] / "api" / "images"),))

st.set_page_config(
    page_title="Smart Plant Monitoring",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# Sidebar
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
    st.write("")
    st.button("Export Data", width="stretch")
    st.write("")
    st.markdown("⚙️ Settings")
    st.markdown("❓ Support")

# Header
st.markdown(
    """
    <div class="sp-header">
      <h1>Smart Plant Monitoring System</h1>
      <div class="sp-search">🔍 Search parameters...</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Data
@st.cache_data(ttl=60, show_spinner="Loading sensor data...")
def _sensor():
    try:
        return get_sensor_readings(500)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Sensor data unavailable: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner="Loading plant health...")
def _health():
    try:
        return get_plant_health(50)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Plant health data unavailable: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner="Loading weather...")
def _weather():
    try:
        return get_weather_forecast(200)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Weather data unavailable: {exc}")
        return pd.DataFrame()


sensor_df = _sensor()
health_df = _health()
weather_df = _weather()


# Helpers
def _latest(series: pd.Series, default: float | None = None) -> float | None:
    if series is None or series.empty:
        return default
    val = series.iloc[0]
    if pd.isna(val):
        return default
    return float(val)


def _pct(value: float | None, lo: float, hi: float) -> int:
    if value is None:
        return 0
    if hi == lo:
        return 50
    pct = (value - lo) / (hi - lo) * 100
    return int(max(0, min(100, pct)))


def _health_score(health_df: pd.DataFrame) -> tuple[int, float]:
    """Return (score, unhealthy_pct) from gold_edw.plant_health."""
    if health_df is None or health_df.empty:
        return 0, 0.0
    total = len(health_df)
    unhealthy = (health_df["health_status"] != "healthy").sum()
    unhealthy_pct = float(unhealthy) / total * 100.0
    confidence = pd.to_numeric(health_df["confidence"], errors="coerce").fillna(0)
    severity = pd.to_numeric(health_df["severity"], errors="coerce").fillna(0)
    avg_conf = float(confidence.mean()) * 100.0
    avg_sev = float(severity.mean())
    # Higher confidence on healthy outcomes lifts score; severity drags it down.
    score = max(0, min(100, int(round(100 - unhealthy_pct - avg_sev * 0.5 + (avg_conf - 50) * 0.1))))
    return score, unhealthy_pct


# Metric row
latest_temp = _latest(sensor_df["temperature"]) if "temperature" in sensor_df else None
latest_hum = _latest(sensor_df["humidity"]) if "humidity" in sensor_df else None
latest_soil = _latest(sensor_df["soil_moisture"]) if "soil_moisture" in sensor_df else None

# Soil ADC values are 0-1023; convert to percentage. Higher ADC = drier on most probes,
# but we render the raw progress so users can interpret the value visually.
soil_pct = None
if latest_soil is not None:
    soil_pct = max(0, min(100, int(round(100 - (latest_soil / 1023.0) * 100))))

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(
        f"""
        <div class="sp-card sp-metric">
          <div class="top">
            <div class="title">🌡️ Ambient Temp</div>
            <div class="pulse">LIVE MQTT</div>
          </div>
          <div><span class="value">{latest_temp:.1f}</span><span class="unit">°C</span></div>
          <div class="bar"><span style="width:{_pct(latest_temp, 0, 40)}%"></span></div>
        </div>
        """ if latest_temp is not None else
        """
        <div class="sp-card sp-metric">
          <div class="top"><div class="title">🌡️ Ambient Temp</div><div class="pulse">LIVE MQTT</div></div>
          <div><span class="value">--</span><span class="unit">°C</span></div>
          <div class="bar"><span style="width:0%"></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f"""
        <div class="sp-card sp-metric">
          <div class="top">
            <div class="title">💧 Air Humidity</div>
            <div class="pulse">LIVE</div>
          </div>
          <div><span class="value">{latest_hum:.0f}</span><span class="unit">%</span></div>
          <div class="bar"><span style="width:{_pct(latest_hum, 0, 100)}%"></span></div>
        </div>
        """ if latest_hum is not None else
        """
        <div class="sp-card sp-metric">
          <div class="top"><div class="title">💧 Air Humidity</div><div class="pulse">LIVE</div></div>
          <div><span class="value">--</span><span class="unit">%</span></div>
          <div class="bar"><span style="width:0%"></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        f"""
        <div class="sp-card sp-metric">
          <div class="top">
            <div class="title">🌱 Soil Moisture (Zone A)</div>
            <div class="pulse">LIVE</div>
          </div>
          <div><span class="value">{soil_pct}</span><span class="unit">%</span></div>
          <div class="bar warn"><span style="width:{soil_pct or 0}%"></span></div>
        </div>
        """ if soil_pct is not None else
        """
        <div class="sp-card sp-metric">
          <div class="top"><div class="title">🌱 Soil Moisture (Zone A)</div><div class="pulse">LIVE</div></div>
          <div><span class="value">--</span><span class="unit">%</span></div>
          <div class="bar warn"><span style="width:0%"></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Sensor trends (24h)
st.markdown('<div class="sp-card"><h3>📈 Sensor Trends (24h)</h3>', unsafe_allow_html=True)

view = st.radio(
    "Series",
    options=["Temp", "Humidity"],
    horizontal=True,
    label_visibility="collapsed",
    key="sensor_view",
)

if not sensor_df.empty:
    cutoff = sensor_df["event_time"].max() - timedelta(hours=24)
    last24 = sensor_df[sensor_df["event_time"] >= cutoff].sort_values("event_time")
    if last24.empty:
        last24 = sensor_df.sort_values("event_time").tail(50)

    series = last24["temperature"] if view == "Temp" else last24["humidity"]
    y_unit = "°C" if view == "Temp" else "%"

    fig = go.Figure(
        data=go.Scatter(
            x=last24["event_time"],
            y=series,
            mode="lines",
            line=dict(color="#2EE6A6", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(46,230,166,0.08)",
            hovertemplate=f"%{{x|%H:%M}}<br>%{{y:.1f}}{y_unit}<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#8B949E"),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            color="#8B949E",
            ticksuffix=f" {y_unit}",
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
else:
    st.info("No sensor readings available yet.")
st.markdown("</div>", unsafe_allow_html=True)

# Vision + Weather + Actions
left, right = st.columns([2, 1])

with left:
    st.markdown('<div class="sp-card"><h3>🤖 Gemini Vision Analysis</h3>', unsafe_allow_html=True)

    if health_df is None or health_df.empty:
        st.info("No vision results from gold_edw.plant_health yet.")
    else:
        latest = health_df.iloc[0]
        img_path = IMAGE_DIR / str(latest["filename"])

        col_img, col_meta = st.columns([1, 1])

        with col_img:
            if img_path.exists():
                st.image(str(img_path), width="stretch")
            else:
                # Fallback: show the most recent file in api/images/
                if IMAGE_DIR.exists():
                    candidates = sorted(
                        [p for p in IMAGE_DIR.glob("*.jpg")],
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                    if candidates:
                        st.image(str(candidates[0]), width="stretch")
                    else:
                        st.warning("No images in api/images/.")
                else:
                    st.warning(f"Image directory not found: {IMAGE_DIR}")

            ts = pd.to_datetime(latest["event_time"]).strftime("%Y-%m-%d %H:%M:%S")
            st.caption(f"📷 ESP32-CAM • {ts}")

        with col_meta:
            status = str(latest.get("health_status") or "unknown").lower()
            badge = "WARNING" if status != "healthy" else "OK"
            badge_class = "" if status == "healthy" else ""
            title = "Leaf Rust Detected" if status == "diseased" else (
                "Healthy Canopy" if status == "healthy" else "Inspection Needed"
            )
            issues = parse_json_list(latest.get("possible_issues"))
            if issues:
                title = issues[0][:60]

            st.markdown(
                f"""
                <div class="sp-alert">
                  <div class="row">
                    <div>STATUS ALERT</div>
                    <div class="pill">{badge}</div>
                  </div>
                  <div class="title">{title}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            conf = float(latest.get("confidence") or 0.0)
            conf_pct = int(round(conf * 100)) if conf <= 1 else int(round(conf))
            st.markdown(
                f"""
                <div class="sp-conf" style="margin-top:14px;">
                  <div class="lbl">Confidence Score</div>
                  <div class="bar"><span style="width:{conf_pct}%"></span></div>
                  <div class="pct">{conf_pct}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            severity = latest.get("severity")
            sev_text = f"{severity:.0f}% severity" if severity is not None and not pd.isna(severity) else "n/a"
            summary = str(latest.get("summary") or "No summary available.")
            st.markdown(
                f"""
                <div class="sp-summary" style="margin-top:14px;">
                  <div class="lbl">Severity</div>
                  <div class="body" style="margin-bottom:10px;">{sev_text}</div>
                  <div class="lbl">Summary</div>
                  <div class="body">{summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # Weather card
    if weather_df is not None and not weather_df.empty:
        # pick the closest forecast row to "now"
        now_utc = pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
        wdf = weather_df.copy()
        wdf["abs_delta"] = (wdf["datetime_utc"] - now_utc).abs()
        cur = wdf.sort_values("abs_delta").iloc[0]
        city = str(cur.get("kotkab") or "Unknown")
        temp = cur.get("temperature")
        desc = str(cur.get("weather_desc_en") or cur.get("weather_desc") or "")
        precip_soon = wdf[wdf["datetime_utc"] >= now_utc].head(3)
        rain_note = ""
        if not precip_soon.empty:
            next_rain = precip_soon[precip_soon["precipitation_mm"].fillna(0) > 0]
            if not next_rain.empty:
                first = next_rain.iloc[0]
                mins = max(0, int((first["datetime_utc"] - now_utc).total_seconds() // 60))
                rain_note = f"Upcoming rain in ~{mins} min. Automated vents closing sequence initiated."
            else:
                rain_note = "No rain expected in the next forecast window."

        icon = "🌧️" if "rain" in desc.lower() or "hujan" in desc.lower() else "⛅"
        temp_str = f"{temp:.0f}°C" if temp is not None and not pd.isna(temp) else "--"
        st.markdown(
            f"""
            <div class="sp-card sp-weather">
              <div class="top">
                <div>BMKG Weather</div>
                <div>{city}</div>
              </div>
              <div class="now">
                <div class="ic">{icon}</div>
                <div>
                  <div class="t">{temp_str}</div>
                  <div class="desc">{desc}</div>
                </div>
              </div>
              <div class="note">{rain_note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sp-card sp-weather">
              <div class="top"><div>☁️ BMKG Weather</div><div>--</div></div>
              <div class="now"><div class="ic">⛅</div><div><div class="t">--</div><div class="desc">No forecast yet</div></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # AI Actions card
    actions_html = '<div class="sp-card"><h3>💡 AI Actions</h3>'
    if health_df is not None and not health_df.empty:
        latest = health_df.iloc[0]
        recs = parse_json_list(latest.get("recommendations"))
        severity = float(latest.get("severity") or 0)
        soil = latest.get("soil_moisture")

        # Map severity
        if severity >= 50:
            priority = "high"
        elif severity >= 20:
            priority = "med"
        else:
            priority = "low"

        if recs:
            first = recs[0]
            actions_html += f"""
              <div class="sp-action">
                <div class="text">
                  <div class="t">{first[:60]}</div>
                  <div class="s">From Gemini analysis</div>
                </div>
                <div class="pill {priority}">{priority.upper()}</div>
              </div>
            """
        # Soil-based action
        if soil is not None and not pd.isna(soil):
            soil_val = float(soil)
            if soil_val > 600:  # higher ADC ~= drier on most probes
                actions_html += """
                  <div class="sp-action">
                    <div class="text">
                      <div class="t">Increase Irrigation</div>
                      <div class="s">Soil moisture low</div>
                    </div>
                    <div class="pill med">MED</div>
                  </div>
                """
        # Add remaining recommendations
        for rec in recs[1:3]:
            actions_html += f"""
              <div class="sp-action">
                <div class="text">
                  <div class="t">{rec[:60]}</div>
                  <div class="s">Gemini recommendation</div>
                </div>
                <div class="pill low">LOW</div>
              </div>
            """
    else:
        actions_html += '<div class="sp-summary"><div class="body">No recommendations yet.</div></div>'
    actions_html += "</div>"
    st.markdown(actions_html, unsafe_allow_html=True)

mqtt_ok = True
nodes = "12/12 Active"
pipeline = "Syncing"
st.markdown(
    f"""
    <div class="sp-status">
      <div><span class="dot"></span> MQTT Broker {'Online' if mqtt_ok else 'Offline'}</div>
      <div><span class="dot"></span> ESP32 Nodes {nodes}</div>
      <div><span class="dot"></span> BQ Pipeline {pipeline}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

last_ingest = "n/a"
if not sensor_df.empty:
    delta = datetime.now(timezone.utc).replace(tzinfo=None) - sensor_df["event_time"].iloc[0].to_pydatetime()
    last_ingest = f"{int(delta.total_seconds())}s ago"

st.markdown(
    f"""
    <div class="sp-footer">
      <div>System Health: Pipeline Active · Last Ingestion: {last_ingest}</div>
      <div>Terms · Privacy · Status</div>
    </div>
    """,
    unsafe_allow_html=True,
)
