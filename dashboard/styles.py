"""Polished CSS for the Smart Plant dashboard.

Streamlit strips <script> tags from st.markdown, so Tailwind Play CDN
won't apply to markdown-rendered HTML. Instead we ship a hand-tuned
stylesheet via st.markdown(unsafe_allow_html=True) which is the
reliable way to style custom HTML in Streamlit.
"""

import streamlit as st


CSS = """
<style>
  :root {
    --bg: #F4F6FA;
    --surface: #FFFFFF;
    --surface-2: #F8FAFC;
    --border: #E5E7EB;
    --border-strong: #D1D5DB;
    --ink: #0F172A;
    --ink-2: #1F2937;
    --muted: #64748B;
    --muted-2: #94A3B8;
    --accent: #10B981;
    --accent-soft: #ECFDF5;
    --warn: #DC2626;
    --warn-soft: #FEF2F2;
    --warn-border: #FCA5A5;
    --amber: #D97706;
    --amber-soft: #FFFBEB;
    --info: #2563EB;
    --info-soft: #EFF6FF;

    --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
    --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
    --radius: 14px;
    --radius-sm: 10px;
  }

  /* Page background */
  html, body, .stApp { background: var(--bg) !important; }
  .stApp [data-testid="stAppViewContainer"] { background: var(--bg) !important; }

  /* Hide Streamlit chrome */
  header [data-testid="stToolbar"] { visibility: hidden; height: 0; }
  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }
  div[data-testid="stDecoration"] { display: none; }

  /* Tighter, wider container */
  .block-container {
    max-width: 1400px;
    padding-top: 1.4rem !important;
    padding-bottom: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0B1220 !important;
    border-right: 1px solid #1E293B;
  }
  section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { margin-bottom: 0.4rem; }

  .sp-brand {
    padding: 8px 8px 18px 8px; border-bottom: 1px solid #1E293B; margin-bottom: 18px;
  }
  .sp-brand .name { color: var(--accent) !important; font-size: 1.15rem; font-weight: 700; letter-spacing: -0.01em; }
  .sp-brand .ver  { color: #64748B !important; font-size: 0.7rem; letter-spacing: .15em; }

  /* Header bar */
  .sp-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 4px 4px 18px 4px;
  }
  .sp-header h1 {
    margin: 0;
    color: var(--ink);
    font-size: 1.55rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .sp-header .sub {
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 2px;
  }

  /* Generic card */
  .sp-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 22px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow .15s ease;
  }
  .sp-card:hover { box-shadow: var(--shadow-md); }
  .sp-card.flush { padding: 0; overflow: hidden; }

  .sp-card-title {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 14px;
  }
  .sp-card-title .t {
    color: var(--ink);
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    display: flex; align-items: center; gap: 8px;
  }
  .sp-card-title .badge {
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: .08em;
    padding: 3px 10px;
    border-radius: 999px;
    text-transform: uppercase;
  }

  /* Insights banner */
  .sp-insights {
    background: linear-gradient(135deg, #ECFDF5 0%, #FFFFFF 60%);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: var(--radius);
    padding: 18px 22px;
    display: flex; align-items: center; justify-content: space-between; gap: 24px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 18px;
  }
  .sp-insights .left { display: flex; align-items: center; gap: 14px; }
  .sp-insights .icon {
    width: 44px; height: 44px; border-radius: 12px;
    background: var(--accent); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; font-weight: 700;
    box-shadow: 0 6px 18px rgba(16, 185, 129, 0.25);
  }
  .sp-insights .kicker {
    color: var(--muted); font-size: 0.7rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600;
  }
  .sp-insights .title { color: var(--ink); font-size: 1.1rem; font-weight: 700; margin-top: 2px; }
  .sp-insights .accent { color: var(--accent); }
  .sp-insights .right { text-align: right; }
  .sp-insights .right .lbl {
    color: var(--muted); font-size: 0.7rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600;
  }
  .sp-insights .right .val { color: var(--warn); font-size: 1.7rem; font-weight: 700; letter-spacing: -0.02em; }

  /* Metric card */
  .sp-metric {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    box-shadow: var(--shadow-sm);
    height: 100%;
    display: flex; flex-direction: column; justify-content: space-between;
    min-height: 138px;
  }
  .sp-metric .top {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 12px;
  }
  .sp-metric .label {
    display: flex; align-items: center; gap: 8px;
    color: var(--ink-2); font-size: 0.85rem; font-weight: 600;
  }
  .sp-metric .icon {
    width: 28px; height: 28px; border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 14px;
  }
  .sp-metric.temp .icon { background: #FEF2F2; color: #DC2626; }
  .sp-metric.hum .icon { background: #EFF6FF; color: #2563EB; }
  .sp-metric.soil .icon { background: #FFFBEB; color: #D97706; }
  .sp-metric .pulse {
    color: var(--accent); font-size: 0.65rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    display: inline-flex; align-items: center; gap: 6px;
  }
  .sp-metric .pulse::before {
    content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
    animation: spPulse 1.6s infinite;
  }
  @keyframes spPulse {
    0%   { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
    70%  { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
  }

  .sp-metric .value-row {
    display: flex; align-items: baseline; gap: 6px; line-height: 1;
  }
  .sp-metric .value {
    font-size: 2.4rem; font-weight: 700; color: var(--ink); letter-spacing: -0.03em;
  }
  .sp-metric .unit { color: var(--muted); font-size: 0.95rem; font-weight: 500; }

  .sp-bar {
    margin-top: 14px; height: 6px; background: #F1F5F9; border-radius: 999px; overflow: hidden;
  }
  .sp-bar > span { display: block; height: 100%; border-radius: 999px; }
  .sp-metric.temp .sp-bar > span { background: linear-gradient(90deg, #FCA5A5, #DC2626); }
  .sp-metric.hum  .sp-bar > span { background: linear-gradient(90deg, #93C5FD, #2563EB); }
  .sp-metric.soil .sp-bar > span { background: linear-gradient(90deg, #FCD34D, #D97706); }

  /* Image card */
  .sp-image {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    box-shadow: var(--shadow-sm);
    height: 100%;
    display: flex; flex-direction: column;
  }
  .sp-image .hd {
    display: flex; align-items: center; justify-content: space-between;
    color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
    padding: 0 4px 10px 4px;
  }
  .sp-image .frame {
    flex: 1; min-height: 220px; border-radius: 10px; overflow: hidden;
    background: #0B1220; position: relative;
    border: 1px solid var(--border);
  }
  .sp-image .frame img {
    width: 100%; height: 100%; object-fit: cover; display: block;
  }
  .sp-image .frame .dot {
    position: absolute; top: 10px; left: 10px;
    background: rgba(15, 23, 42, 0.85); color: #fff;
    font-size: 0.65rem; font-weight: 600; letter-spacing: .1em;
    padding: 4px 10px; border-radius: 999px;
    display: inline-flex; align-items: center; gap: 6px;
  }
  .sp-image .frame .dot::before {
    content: ""; width: 6px; height: 6px; border-radius: 50%; background: #EF4444;
  }
  .sp-image .ts { color: var(--muted); font-size: 0.78rem; padding: 10px 4px 2px 4px; }

  /* Status alert (vision) */
  .sp-alert {
    background: var(--warn-soft);
    border: 1px solid var(--warn-border);
    border-radius: 12px;
    padding: 14px 16px;
  }
  .sp-alert.ok { background: var(--accent-soft); border-color: #A7F3D0; }
  .sp-alert .row {
    display: flex; align-items: center; justify-content: space-between;
    color: var(--muted); font-size: 0.7rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase;
  }
  .sp-alert .pill {
    color: #fff; background: var(--warn);
    font-size: 0.65rem; font-weight: 700; letter-spacing: .14em;
    padding: 3px 10px; border-radius: 999px;
  }
  .sp-alert.ok .pill { background: var(--accent); }
  .sp-alert .title {
    color: var(--warn); font-size: 1.15rem; font-weight: 700; margin-top: 6px;
  }
  .sp-alert.ok .title { color: #065F46; }

  /* Confidence */
  .sp-conf .lbl {
    color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
  }
  .sp-conf .bar {
    height: 8px; border-radius: 999px; background: #F1F5F9;
    margin: 8px 0; overflow: hidden;
  }
  .sp-conf .bar > span {
    display: block; height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, #34D399, #10B981);
  }
  .sp-conf .pct { color: var(--ink); font-weight: 700; text-align: right; font-size: 0.85rem; }

  /* Summary block */
  .sp-summary .lbl {
    color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
    margin-top: 12px;
  }
  .sp-summary .body { color: var(--ink-2); font-size: 0.92rem; line-height: 1.55; margin-top: 4px; }

  /* Weather */
  .sp-weather .top {
    display: flex; align-items: center; justify-content: space-between;
    color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
    margin-bottom: 12px;
  }
  .sp-weather .now { display: flex; align-items: center; gap: 14px; }
  .sp-weather .now .ic {
    width: 52px; height: 52px; border-radius: 14px;
    background: linear-gradient(135deg, #DBEAFE, #EFF6FF);
    color: #2563EB;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 24px;
  }
  .sp-weather .now .t {
    font-size: 2rem; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; line-height: 1;
  }
  .sp-weather .desc { color: var(--muted); font-size: 0.85rem; margin-top: 4px; }
  .sp-weather .note {
    margin-top: 14px;
    background: var(--info-soft);
    border: 1px solid #BFDBFE;
    border-radius: 10px; padding: 10px 12px;
    color: #1E3A8A; font-size: 0.82rem;
  }

  /* AI Action rows */
  .sp-action {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 10px; padding: 12px 14px;
    margin-top: 10px;
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
  }
  .sp-action .text .t {
    color: var(--ink); font-size: 0.9rem; font-weight: 600; letter-spacing: -0.01em;
  }
  .sp-action .text .s { color: var(--muted); font-size: 0.76rem; margin-top: 2px; }
  .sp-action .pill {
    font-size: 0.65rem; font-weight: 700; letter-spacing: .14em;
    padding: 4px 10px; border-radius: 999px; text-transform: uppercase;
  }
  .sp-action .pill.high { background: #FEF2F2; color: #B91C1C; border: 1px solid #FCA5A5; }
  .sp-action .pill.med  { background: #FFFBEB; color: #B45309; border: 1px solid #FCD34D; }
  .sp-action .pill.low  { background: var(--accent-soft); color: #047857; border: 1px solid #A7F3D0; }

  /* Status strip */
  .sp-strip {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 20px;
    display: flex; align-items: center; gap: 28px; flex-wrap: wrap;
    color: var(--muted); font-size: 0.85rem;
    box-shadow: var(--shadow-sm);
    margin-top: 14px;
  }
  .sp-strip .item { display: inline-flex; align-items: center; gap: 8px; }
  .sp-strip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
  .sp-strip .dot.warn { background: var(--amber); }
  .sp-strip .dot.err { background: var(--warn); }
  .sp-strip .item .v { color: var(--ink-2); font-weight: 600; }

  /* Footer */
  .sp-footer {
    display: flex; align-items: center; justify-content: space-between;
    color: var(--muted); font-size: 0.78rem; padding: 18px 4px 0 4px;
  }
  .sp-footer a { color: var(--muted); margin-left: 14px; text-decoration: none; }
  .sp-footer a:hover { color: var(--ink); }

  /* Plotly tweaks */
  .js-plotly-plot .plotly { background: transparent !important; }

  /* Streamlit's radio horizontal wrapping */
  div[data-testid="stRadio"] > div { gap: 6px; }
  div[data-testid="stRadio"] label {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 4px 12px !important;
    font-size: 0.78rem !important;
  }
</style>
"""


def injectStyles() -> None:
    """Inject the dashboard stylesheet. Call once near the top of app.py."""
    st.markdown(CSS, unsafe_allow_html=True)
