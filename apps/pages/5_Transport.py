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
import plotly.express as px
import plotly.graph_objects as go

from campus_intel.config import get_paths
from campus_intel.db import connect_sqlite
from campus_intel.recommend import analyze_transport
from apps.utils import (
    inject_css, page_header, section_header, kpi_card,
    make_daily_line, make_heatmap, make_scatter, make_bar,
    insight_card, alert_card
)

st.set_page_config(page_title="Transport Analytics", layout="wide", page_icon="")
inject_css()

check_data_loaded("dataset_transport")
df = st.session_state["dataset_transport"]

if df.empty:
    st.warning("No data found.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
view_range = st.sidebar.radio("Time Window", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "All"])
routes     = st.sidebar.multiselect("Routes", df["route"].unique(), default=[df["route"].unique()[0]])

if view_range == "Last 7 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=7)]
elif view_range == "Last 14 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=14)]
elif view_range == "Last 30 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=30)]
df = df[df["route"].isin(routes)]

# ── Header & KPIs ─────────────────────────────────────────────────────────────
page_header("", "Campus Shuttle Transport", "Route tracking, load factors, and delay analysis.")

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Avg Passg / Trip", f"{df['passenger_count'].mean():.0f}", "", "")
with c2: kpi_card("Peak Passg", f"{df['passenger_count'].max()}", "", "")
with c3: kpi_card("Avg Delay", f"{df['delay_minutes'].mean():.1f} mins", "", "")
rain_d = df[df["rain"] > 5]["delay_minutes"].mean()
with c4: kpi_card("Avg Delay (Rain)", f"{rain_d:.1f} mins" if not pd.isna(rain_d) else "N/A", "", "")
st.markdown("---")

t1, t2, t3, t4 = st.tabs([" Charts", " Benefits & Savings", " Smart Tips", " Test Changes"])

# ── Tab 1: Analytics ─────────────────────────────────────────────────────────
with t1:
    c_t1, c_t2 = st.columns([4, 1])
    with c_t2: show_fc = st.toggle(" Show Future Forecast", key="trans_fc")
    daily = df.groupby([df["ts"].dt.date.rename("date"), "route"], as_index=False)["passenger_count"].mean().round(0)
    st.plotly_chart(make_daily_line(daily, "date", "passenger_count", color_col="route", title="Daily Passenger Volume by Route", show_forecast=show_fc), width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_scatter(df.sample(min(800, len(df))), "rain", "delay_minutes", "route", title="Delays Correlated with Rainfall"), width='stretch')
    with col2:
        df["hour"] = df["ts"].dt.hour
        df["dow"]  = df["ts"].dt.day_name()
        pivot = df.pivot_table(values="passenger_count", index="dow", columns="hour", aggfunc="mean")
        st.plotly_chart(make_heatmap(pivot, "Hourly Passenger Heatmap", "YlOrRd"), width='stretch')

# ── Tab 2: Savings & Benefits ────────────────────────────────────────────────
with t2:
    section_header("Bus Route Improvements")
    col1, col2 = st.columns(2)
    with col1:
        insight_card("Extra Buses During Rain", 
            "**Measure:** Detect rain > 5mm and automatically dispatch 1 backup standby shuttle.<br>"
            "**If you do this:** Mitigates the 2x wait time spike.<br>"
            "** Benefit:** Halves student delay time during severe weather.", "#4fc3f7")
    with col2:
        insight_card("Store Buses During Empty Hours", 
            "**Measure:** Park shuttles between 2 PM - 4 PM when load < 5 students.<br>"
            "**If you do this:** Saves massive idle engine fuel.<br>"
            "** Benefit:** Extrapolated 8% fuel savings per month without impacting satisfaction.", "#66bb6a")

# ── Tab 3: AI Insights ───────────────────────────────────────────────────────
with t3:
    section_header("AI Transport Strategist")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key: alert_card("Set `GROQ_API_KEY` in `.env` for AI insights.", "warning")
    else:
        if st.button("Generate Transport Insights", type="primary"):
            with st.spinner("Analyzing fleet data..."):
                st.markdown(analyze_transport(api_key, df))

# ── Tab 4: Future Predictions ────────────────────────────────────────────────
with t4:
    section_header("Bus Delay Simulator")
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        add_buses = st.slider("Add Extra Buses", 0, 5, 0)
        demand_increase = st.slider("Expected Load Increase (%)", 0, 50, 10)
        
    with pc2:
        base_del = df["delay_minutes"].mean()
        
        # Simple mock
        new_del = base_del * (1 + demand_increase/100) * (1 - (add_buses * 0.15))
        new_del = max(0.0, new_del)
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: kpi_card("Predicted Avg Delay", f"{new_del:.1f} m", f"{new_del-base_del:.1f} m shift", "", delta_good=new_del <= base_del)
        with c_p2: alert_card("Traffic threshold crossed." if new_del > 15 else "Flow is optimal.", "danger" if new_del>15 else "success")
        
        st.plotly_chart(px.bar(pd.DataFrame({"State":["Current Baseline", "Forecasted Result"], "Delay":[base_del, new_del]}), x="State", y="Delay", color="State", color_discrete_sequence=["#4fc3f7","#ef5350" if new_del>base_del else "#66bb6a"]), width='stretch')
