# app.py — Store Intelligence Dashboard
# Run: streamlit run app.py
#
# Reads data from the FastAPI backend (default: http://localhost:8000)
# Set API_BASE env var to change the API URL.

import os
import time
import requests
import streamlit as st

# ── Config ───────────────────────────────────────────────────────────────────
API_BASE      = os.environ.get("API_BASE", "http://localhost:8000")
REFRESH_SECS  = 5

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Store Intelligence",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dark theme overrides ──────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #0e1117; color: #e0e0e0; }

  .metric-card {
    background: #1c1f26;
    border: 1px solid #2e333d;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
  }
  .metric-label {
    font-size: 13px; color: #8a8f9e;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;
  }
  .metric-value { font-size: 34px; font-weight: 700; color: #ffffff; line-height: 1.1; }
  .metric-sub   { font-size: 12px; color: #4caf8a; margin-top: 4px; }

  .section-header {
    font-size: 16px; font-weight: 600; color: #c8cdd8;
    border-left: 3px solid #4f8ef7; padding-left: 10px; margin: 28px 0 14px 0;
  }

  .funnel-row { margin-bottom: 10px; }
  .funnel-label { font-size: 13px; color: #8a8f9e; margin-bottom: 3px; }
  .funnel-bar-bg {
    background: #1c1f26; border-radius: 6px;
    height: 32px; width: 100%; position: relative; overflow: hidden;
  }
  .funnel-bar-fill {
    height: 100%; border-radius: 6px;
    display: flex; align-items: center;
    padding-left: 12px; font-size: 13px; font-weight: 600; color: #fff;
  }

  .badge-crowd  { background:#c0392b22; border:1px solid #c0392b; color:#e74c3c; }
  .badge-loiter { background:#e67e2222; border:1px solid #e67e22; color:#f39c12; }
  .badge-queue  { background:#8e44ad22; border:1px solid #8e44ad; color:#9b59b6; }
  .badge-base {
    display:inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 6px;
  }

  .zone-table { width:100%; border-collapse:collapse; }
  .zone-table th {
    text-align:left; font-size:12px; color:#8a8f9e;
    text-transform:uppercase; letter-spacing:.06em;
    border-bottom:1px solid #2e333d; padding:6px 10px;
  }
  .zone-table td { padding:9px 10px; font-size:14px; border-bottom:1px solid #1c1f26; color:#d0d4de; }
  .heat-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }

  .anom-row {
    background:#1c1f26; border-radius:8px; padding:10px 14px; margin-bottom:6px;
    display:flex; justify-content:space-between; align-items:center; font-size:13px;
  }
  .anom-ts { color:#555a66; font-size:11px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch(path: str, fallback=None):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


def card(label: str, value, sub: str = ""):
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)


FUNNEL_COLOURS = ["#4f8ef7", "#4fbbf7", "#4fd9a0", "#f7c94f"]

ZONE_HEAT_COLOURS = {
    "entrance":     "#4f8ef7",
    "skin_care":    "#f79c4f",
    "makeup":       "#e84fda",
    "foh":          "#4fbbf7",
    "cash_counter": "#e84f4f",
    "bottom_shelf": "#9b59b6",
    "floor":        "#555a66",
}

ANOMALY_LABEL = {
    "anomaly_crowd":  ("🔴 Overcrowding", "badge-crowd"),
    "anomaly_loiter": ("🟡 Loitering",    "badge-loiter"),
    "anomaly_queue":  ("🟣 Queue Buildup","badge-queue"),
}


# ── Main render ───────────────────────────────────────────────────────────────
def render():
    st.markdown(
        "<h2 style='margin-bottom:2px;color:#fff'>🏪 Store Intelligence</h2>"
        "<p style='color:#555a66;font-size:13px;margin-top:0'>Brigade Road · Live Analytics</p>",
        unsafe_allow_html=True,
    )

    metrics   = fetch("/metrics",       fallback={})
    funnel    = fetch("/funnel",        fallback={})
    heatmap   = fetch("/zones/heatmap", fallback={})
    anomalies = fetch("/anomalies",     fallback={})

    status_col, _ = st.columns([1, 5])
    with status_col:
        if metrics:
            st.success("API connected", icon="✅")
        else:
            st.error("API unreachable — start FastAPI first", icon="⚠️")

    # ── 1. Metric cards ───────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Live Metrics</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Total Footfall", metrics.get("total_entries", "—"))
    with c2:
        rate = metrics.get("conversion_rate_pct", "—")
        card("Conversion Rate", f"{rate}%" if rate != "—" else "—", "billing reached")
    with c3:
        dwell = metrics.get("avg_dwell_seconds", "—")
        card("Avg Dwell Time", f"{dwell}s" if dwell != "—" else "—")
    with c4:
        card("Currently Inside", metrics.get("currently_inside", "—"),
             f"peak {metrics.get('peak_occupancy', '—')}")

    # ── 2. Funnel ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Conversion Funnel</div>', unsafe_allow_html=True)
    stages    = funnel.get("stages") or []
    max_count = max((s.get("count", 0) for s in stages), default=1) or 1

    for i, stage in enumerate(stages):
        count  = stage.get("count", 0)
        label  = stage.get("stage", "").replace("_", " ").title()
        drop   = stage.get("drop_off_pct", 0)
        colour = FUNNEL_COLOURS[i % len(FUNNEL_COLOURS)]
        pct    = int(count / max_count * 100)
        drop_txt = f"  ↓ {drop}% drop-off" if drop > 0 else ""
        st.markdown(f"""
        <div class="funnel-row">
          <div class="funnel-label">{label} — <strong style="color:#fff">{count}</strong>{drop_txt}</div>
          <div class="funnel-bar-bg">
            <div class="funnel-bar-fill" style="width:{pct}%;background:{colour};">{count}</div>
          </div>
        </div>""", unsafe_allow_html=True)

    overall = funnel.get("overall_conversion_pct", 0)
    st.markdown(
        f"<p style='color:#4caf8a;font-size:13px;margin-top:6px'>"
        f"Overall conversion: <strong>{overall}%</strong></p>",
        unsafe_allow_html=True,
    )

    # ── 3 & 4 side by side ────────────────────────────────────────────────────
    col_zone, col_anom = st.columns(2)

    # ── 3. Zone heatmap ───────────────────────────────────────────────────────
    with col_zone:
        st.markdown('<div class="section-header">Zone Heatmap</div>', unsafe_allow_html=True)
        zones = heatmap.get("zones") or []
        if zones:
            rows_html = ""
            for z in zones:
                zname  = z.get("zone", "")
                colour = ZONE_HEAT_COLOURS.get(zname, "#888")
                vis    = z.get("unique_visitors", 0)
                dwell  = z.get("avg_dwell_seconds", 0)
                rows_html += f"""
                <tr>
                  <td><span class="heat-dot" style="background:{colour}"></span>
                      {zname.replace('_',' ').title()}</td>
                  <td style="text-align:center">{vis}</td>
                  <td style="text-align:center">{dwell}s</td>
                </tr>"""
            st.markdown(f"""
            <table class="zone-table">
              <thead><tr>
                <th>Zone</th>
                <th style="text-align:center">Visitors</th>
                <th style="text-align:center">Avg Dwell</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>""", unsafe_allow_html=True)
        else:
            st.info("No zone data yet. Run the detection pipeline first.")

    # ── 4. Anomalies ──────────────────────────────────────────────────────────
    with col_anom:
        st.markdown('<div class="section-header">Anomaly Alerts</div>', unsafe_allow_html=True)
        summary = anomalies.get("summary") or []
        if summary:
            badges = ""
            for s in summary:
                etype = s.get("event_type", "")
                count = s.get("count", 0)
                label, css = ANOMALY_LABEL.get(etype, (etype, "badge-loiter"))
                badges += f'<span class="badge-base {css}">{label} × {count}</span>'
            st.markdown(f"<div style='margin-bottom:12px'>{badges}</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<p style='color:#4caf8a;font-size:13px'>✅ No anomalies detected</p>",
                unsafe_allow_html=True,
            )

        events = (anomalies.get("events") or [])[:10]
        for ev in events:
            etype      = ev.get("event_type", "")
            ts         = ev.get("timestamp", "")[:19].replace("T", " ")
            zone       = ev.get("zone") or ""
            meta       = ev.get("metadata") or ""
            label, css = ANOMALY_LABEL.get(etype, (etype, "badge-loiter"))
            detail     = f"zone: {zone}" if zone else meta
            st.markdown(f"""
            <div class="anom-row">
              <span>
                <span class="badge-base {css}">{label}</span>
                <span style="color:#c8cdd8">{detail}</span>
              </span>
              <span class="anom-ts">{ts}</span>
            </div>""", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<p style='color:#333a44;font-size:11px;text-align:center;margin-top:24px'>"
        f"Auto-refreshing every {REFRESH_SECS}s · API: {API_BASE} · Store Intelligence v1.0</p>",
        unsafe_allow_html=True,
    )


render()
time.sleep(REFRESH_SECS)
st.rerun()
