import sys, os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "src"))
load_dotenv(root_dir / ".env")

import pandas as pd
import streamlit as st
from apps.utils import check_data_loaded
import plotly.graph_objects as go
import plotly.express as px

from campus_intel.config import get_paths
from campus_intel.db import connect_sqlite
from campus_intel.recommend import analyze_wifi
from apps.utils import (
    inject_css, page_header, section_header, kpi_card,
    make_daily_line, make_heatmap, make_scatter, make_bar,
    insight_card, alert_card
)

st.set_page_config(page_title="WiFi Analytics", layout="wide", page_icon="")
inject_css()

check_data_loaded("dataset_wifi")
df = st.session_state["dataset_wifi"]

if df.empty:
    st.warning("No data found.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
view_range = st.sidebar.radio("Time Window", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "All"])
all_aps = df["ap_id"].unique().tolist()
aps = st.sidebar.multiselect("Access Points", all_aps, default=[all_aps[0]])

if view_range == "Last 7 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=7)]
elif view_range == "Last 14 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=14)]
elif view_range == "Last 30 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=30)]
df = df[df["ap_id"].isin(aps)]

# ── Header & KPIs ─────────────────────────────────────────────────────────────
page_header("", "WiFi Network Intelligence", "Device connections, internet speed, and network health by building.")

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Avg Connected Devices", f"{df['connected_devices'].mean():.0f}", "", "")
with c2: kpi_card("Busiest Hour (Devices)", f"{df['connected_devices'].max()} devices", "", "")
with c3: kpi_card("Avg Network Delay", f"{df['network_delay'].mean():.1f} ms", "", "")
with c4: kpi_card("Avg Signal Drops", f"{df['connection_drops'].mean():.2f}%", "", "", delta_good=df['connection_drops'].mean()<2.0)
st.markdown("---")

t1, t2, t3, t4 = st.tabs([" Charts", " Benefits & Savings", " Smart Tips", " Test Changes"])

# ── Tab 1: Analytics ─────────────────────────────────────────────────────────
with t1:
    c_t1, c_t2 = st.columns([4, 1])
    with c_t2: show_fc = st.toggle(" Show Future Forecast", key="wifi_fc")
    daily_bld = df.groupby([df["ts"].dt.date.rename("date"), "building_id"], as_index=False)["connected_devices"].mean().round(0)
    st.plotly_chart(make_daily_line(daily_bld, "date", "connected_devices", color_col="building_id", title="Daily Avg WiFi Load by Building", show_forecast=show_fc), width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_scatter(df.sample(min(800, len(df))), "connected_devices", "network_delay", "connection_drops", title="Internet Delay vs Number of Users"), width='stretch')
    with col2:
        ap_rank = df.groupby("ap_id", as_index=False)["network_delay"].mean().round(1).sort_values("network_delay", ascending=False).head(10)
        st.plotly_chart(make_bar(ap_rank, "ap_id", "network_delay", title="Access Points Ranked by Slowest Response", color="#ef5350"), width='stretch')

# ── Tab 2: Savings & Benefits ────────────────────────────────────────────────
with t2:
    section_header("Internet Improvements & Savings")
    col1, col2 = st.columns(2)
    with col1:
        insight_card("Deploy WiFi 6 APs in High-Density Zones", 
            "**Measure:** Upgrade the top 3 worst performing APs from the Analytics chart.<br>"
            "**If you do this:** Supports 4x more concurrent users per AP.<br>"
            "** Benefit:** Completely eliminates latency spikes above >150ms during exam week.", "#4fc3f7")
    with col2:
        insight_card("Implement Device Timeout Filters", 
            "**Measure:** Force drops on idle connections > 60m.<br>"
            "**If you do this:** Clears ghost devices hanging onto AP slots.<br>"
            "** Benefit:** Increases available IP pool by ~14% without hardware upgrades.", "#66bb6a")

# ── Tab 3: AI Insights ───────────────────────────────────────────────────────
with t3:
    section_header("Domain-Specific Network Strategy")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key: alert_card("Set `GROQ_API_KEY` in `.env` for AI insights.", "warning")
    else:
        if st.button("Generate Network Insights", type="primary"):
            with st.spinner("Analyzing AP telemetry..."):
                st.markdown(analyze_wifi(api_key, df))

# ── Tab 4: Future Predictions ────────────────────────────────────────────────
with t4:
    section_header("Network Capacity Modeler")
    st.markdown("Simulate capacity upgrades and their effect on student latency.")
    
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        user_growth = st.slider("Projected User Growth (%)", 0, 100, 20)
        bw_upgrade  = st.slider("Bandwidth Controller Upgrade (Gbps)", 0, 10, 0)
        
    with pc2:
        base_lat = df["network_delay"].mean()
        
        # Mock formula representing queueing theory
        new_users = df["connected_devices"].mean() * (1 + (user_growth/100))
        # Increase latency based on load factor, decrease based on bandwidth upgrade
        new_lat = base_lat * (1 + (user_growth/50)**2) * (1 - min(0.8, bw_upgrade*0.1))
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: kpi_card("Predicted Latency", f"{new_lat:.1f} ms", f"{int(new_lat - base_lat)} ms change", "", delta_good=(new_lat <= base_lat))
        with c_p2:
            alert_msg = "Critical Degradation Expected!" if new_lat > 100 else "Network Stable."
            alert_card(alert_msg, "danger" if new_lat > 100 else "success")
        
        chart_df = pd.DataFrame({"Scenario":["Current Baseline", "Forecasted Result"], "Latency (ms)":[base_lat, new_lat]})
        st.plotly_chart(px.bar(chart_df, x="Scenario", y="Latency (ms)", color="Scenario", color_discrete_sequence=["#4fc3f7", "#ef5350" if new_lat>100 else "#66bb6a"]), width='stretch')
