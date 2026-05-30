"""Reusable CSS for the Smart Plant dashboard."""

CSS = """
<style>
  :root {
    --bg-card: #161B26;
    --bg-card-2: #1B2230;
    --border: rgba(255,255,255,0.06);
    --muted: #8B949E;
    --accent: #2EE6A6;
    --warn: #F87171;
    --warn-bg: rgba(248,113,113,0.12);
  }

  /* Hide default Streamlit chrome bits */
  header [data-testid="stToolbar"] { visibility: hidden; }
  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }

  .block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
    max-width: 1400px;
  }

  /* Page header */
  .sp-header {
    display:flex; align-items:center; justify-content:space-between;
    padding: 4px 4px 14px 4px;
  }
  .sp-header h1 {
    font-size: 1.35rem; margin: 0; color: #E6EDF3; font-weight: 600;
  }
  .sp-search {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 10px; padding: 6px 12px; color: var(--muted); font-size: 0.85rem;
    min-width: 280px; display: inline-flex; align-items:center; gap:8px;
  }

  /* Generic card */
  .sp-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 14px; padding: 18px 20px; margin-bottom: 14px;
  }
  .sp-card h3 {
    margin: 0 0 10px 0; font-size: 0.95rem; color: #C9D1D9; font-weight: 600;
    display:flex; align-items:center; gap:8px;
  }
  .sp-card .label { color: var(--muted); font-size: 0.78rem; letter-spacing: .04em; }

  /* Metric cards */
  .sp-metric { padding: 18px 20px; }
  .sp-metric .top {
    display:flex; align-items:center; justify-content:space-between;
    color: var(--muted); font-size: 0.82rem; margin-bottom: 8px;
  }
  .sp-metric .title { display:flex; align-items:center; gap:8px; color: #C9D1D9; }
  .sp-metric .pulse { color: var(--accent); font-size: 0.7rem; letter-spacing: .12em; }
  .sp-metric .pulse::before {
    content:""; display:inline-block; width:6px; height:6px;
    background: var(--accent); border-radius:50%; margin-right:6px; vertical-align:middle;
  }
  .sp-metric .value {
    font-size: 2.1rem; font-weight: 600; color: #E6EDF3; letter-spacing: -0.02em;
  }
  .sp-metric .unit { color: var(--muted); font-size: 0.95rem; margin-left: 4px; }
  .sp-metric .bar {
    height: 4px; border-radius: 4px; background: rgba(255,255,255,0.05);
    margin-top: 14px; overflow:hidden;
  }
  .sp-metric .bar > span { display:block; height:100%; background: var(--accent); }
  .sp-metric .bar.warn > span { background: #F4B43B; }

  /* Status alert */
  .sp-alert {
    background: var(--warn-bg);
    border: 1px solid rgba(248,113,113,0.25);
    border-radius: 10px; padding: 12px 14px; color: #F8D7DA;
  }
  .sp-alert .row {
    display:flex; align-items:center; justify-content:space-between;
    color: var(--muted); font-size: 0.72rem; letter-spacing: .12em;
  }
  .sp-alert .pill {
    background: var(--warn); color: #fff; font-weight: 600;
    font-size: 0.65rem; padding: 2px 8px; border-radius: 999px; letter-spacing: .12em;
  }
  .sp-alert .title { color: #FCA5A5; font-size: 1.1rem; font-weight: 600; margin-top: 4px; }

  /* Confidence */
  .sp-conf .lbl { color: var(--muted); font-size: 0.78rem; }
  .sp-conf .bar {
    height: 6px; border-radius: 6px; background: rgba(255,255,255,0.06);
    margin: 6px 0 4px 0; overflow:hidden;
  }
  .sp-conf .bar > span { display:block; height: 100%; background: var(--accent); }
  .sp-conf .pct { color: var(--accent); font-weight: 600; text-align:right; font-size: 0.82rem; }

  /* Severity / summary block */
  .sp-summary .lbl { color: var(--muted); font-size: 0.78rem; }
  .sp-summary .body { color: #C9D1D9; font-size: 0.9rem; line-height: 1.45; }

  /* Weather */
  .sp-weather .top {
    display:flex; align-items:center; justify-content:space-between;
    color: var(--muted); font-size: 0.78rem; margin-bottom: 8px;
  }
  .sp-weather .now {
    display:flex; align-items:center; gap:14px;
  }
  .sp-weather .now .ic { font-size: 30px; }
  .sp-weather .now .t { font-size: 2rem; font-weight: 600; color: #E6EDF3; }
  .sp-weather .desc { color: var(--muted); font-size: 0.82rem; margin-top: 2px;}
  .sp-weather .note {
    margin-top: 12px;
    background: var(--bg-card-2);
    border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 12px;
    color: #C9D1D9; font-size: 0.8rem;
  }

  /* AI Actions */
  .sp-action {
    background: var(--bg-card-2); border: 1px solid var(--border);
    border-radius: 10px; padding: 10px 12px; margin-top: 8px;
    display:flex; align-items:center; justify-content:space-between; gap: 8px;
  }
  .sp-action .text .t { color: #E6EDF3; font-size: 0.85rem; font-weight: 500; }
  .sp-action .text .s { color: var(--muted); font-size: 0.74rem; }
  .sp-action .pill {
    font-size: 0.65rem; font-weight: 700; letter-spacing: .12em;
    padding: 3px 8px; border-radius: 999px;
  }
  .sp-action .pill.high { background: rgba(248,113,113,.18); color:#FCA5A5; }
  .sp-action .pill.med  { background: rgba(244,180,59,.18);  color:#F4B43B; }
  .sp-action .pill.low  { background: rgba(46,230,166,.18);  color: var(--accent); }

  /* System status row */
  .sp-status {
    display:flex; gap:24px; flex-wrap: wrap;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; padding: 12px 18px; margin-top: 10px;
    color: var(--muted); font-size: 0.82rem;
  }
  .sp-status .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background: var(--accent); margin-right: 8px; }

  /* Footer */
  .sp-footer {
    display:flex; align-items:center; justify-content:space-between;
    color: var(--muted); font-size: 0.75rem; padding: 14px 4px 0 4px;
  }

  /* Sidebar tweaks */
  section[data-testid="stSidebar"] {
    background: #0B0F17;
    border-right: 1px solid var(--border);
  }
  .sp-brand .name { color: var(--accent); font-size: 1.1rem; font-weight: 700; }
  .sp-brand .ver  { color: var(--muted); font-size: 0.72rem; letter-spacing: .12em; }
</style>
"""
