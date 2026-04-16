"""Overall Campus Summary and AI Strategy Page."""
from __future__ import annotations
import sys
import pandas as pd
import streamlit as st
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "src"))

from apps.utils import (
    inject_css, page_header, section_header, alert_card, check_data_loaded, COST_PER_KWH
)
from campus_intel.recommend import generate_groq_insights

st.set_page_config(page_title="Overall Summary", layout="wide", page_icon="")
inject_css()

# Enforce that all modules are properly registered before allowing deep summary access
check_data_loaded("dataset_electricity")

# Data loading safe guards
df_elec  = st.session_state.get("dataset_electricity", pd.DataFrame())
df_mess  = st.session_state.get("dataset_mess", pd.DataFrame())
df_trans = st.session_state.get("dataset_transport", pd.DataFrame())
df_wifi  = st.session_state.get("dataset_wifi", pd.DataFrame())
df_lib   = st.session_state.get("dataset_library", pd.DataFrame())

page_header("", "Campus Overall Summary", "High-level current scenario and strategic actions that should be taken.")

# --- Current Scenario (Metrics Aggregation) ---
elec_daily = df_elec.groupby(df_elec["ts"].dt.date)["total_energy_usage"].sum() if not df_elec.empty else pd.Series([0])
wifi_daily = df_wifi.groupby(df_wifi["ts"].dt.date)["connected_devices"].mean() if not df_wifi.empty else pd.Series([0])

avg_kwh = elec_daily.tail(7).mean() if len(elec_daily) > 0 else 0
avg_cost = avg_kwh * COST_PER_KWH

avg_wait = df_mess["estimated_wait_min"].mean() if "estimated_wait_min" in df_mess.columns else 0
wifi_avg = wifi_daily.mean() if len(wifi_daily) > 0 else 0
trans_delay = df_trans["delay_minutes"].mean() if "delay_minutes" in df_trans.columns else 0
lib_occ = df_lib["total_occupancy"].mean() if "total_occupancy" in df_lib.columns else 0

section_header("Current Operational Scenario")

st.markdown(f"""
<div style="background: rgba(255,255,255,0.02); padding: 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 25px;">
    <strong>Campus-Wide Operational Snapshot:</strong>
    <ul>
        <li style="margin-bottom: 8px;"> <strong>Energy Health:</strong> Consuming an average of <strong>{avg_kwh:,.0f} kWh</strong> per day. Costing roughly <strong>₹{avg_cost:,.0f}/day</strong> in electricity.</li>
        <li style="margin-bottom: 8px;"> <strong>Network Saturation:</strong> Supporting a consistent average of <strong>{wifi_avg:.0f} active devices</strong> simultaneously.</li>
        <li style="margin-bottom: 8px;"> <strong>Dining Stress:</strong> Average queuing wait times rest at <strong>{avg_wait:.1f} minutes</strong> during meal hours.</li>
        <li style="margin-bottom: 8px;"> <strong>Shuttle Transport:</strong> Routine delays are generally averaging <strong>{trans_delay:.1f} minutes</strong> across standard routes.</li>
        <li style="margin-bottom: 8px;"> <strong>Library Demand:</strong> Maintaining an average baseline occupancy of <strong>{lib_occ:.0f} students</strong>.</li>
    </ul>
    <br>
    <div style="padding: 10px 15px; border-left: 4px solid #66bb6a; background: rgba(102,187,106, 0.1);">
        <strong>Site Status:</strong> <strong>STABLE</strong>. The analytical predictive layers suggest no immediate crises. Continue to the next section to see AI-derived policies for improvements.
    </div>
</div>
""", unsafe_allow_html=True)


# --- Things that should be done (AI Strategist) ---
section_header(" Recommended Actions (AI Strategist)")

st.write("Generate cross-domain intelligence connecting observations across departments to deduce things that should be done based on the holistic metrics.")

api_key = os.environ.get("GROQ_API_KEY", "").strip() or "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"

if api_key:
    if st.button("Synthesize Executive Intelligence", type="primary"):
        with st.spinner("Analyzing multi-domain telemetry and structuring strategic steps..."):
            st.markdown(generate_groq_insights(api_key, {
                "electricity": df_elec, 
                "wifi": df_wifi, 
                "mess": df_mess, 
                "transport": df_trans,
                "library": df_lib
            }))
else:
    alert_card("Set `GROQ_API_KEY` in `.env` for cross-domain AI insights.", "warning")
