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
from campus_intel.recommend import analyze_electricity
from apps.utils import (
    inject_css, page_header, section_header, kpi_card,
    make_daily_line, make_heatmap, make_scatter, make_bar,
    COST_PER_KWH, CO2_PER_KWH, insight_card, alert_card
)

st.set_page_config(page_title="Electricity Intelligence", layout="wide", page_icon="")
inject_css()

check_data_loaded("dataset_electricity")
df = st.session_state["dataset_electricity"]

if df.empty:
    st.warning("No data found.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
view_range = st.sidebar.radio("Time Window", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "All"])
buildings  = st.sidebar.multiselect("Buildings", df["building_id"].unique(), default=[df["building_id"].unique()[0]])

if view_range == "Last 7 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=7)]
elif view_range == "Last 14 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=14)]
elif view_range == "Last 30 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=30)]
df = df[df["building_id"].isin(buildings)]

# ── Header & KPIs ─────────────────────────────────────────────────────────────
page_header("", "Electricity Intelligence", "Power usage by building, cooling loads, and energy saving opportunities.")

tot_kwh     = df['total_energy_usage'].sum()
avg_kwh     = df['total_energy_usage'].mean()
peak_power_drain     = df['peak_power_drain'].max()
cooling_share  = (df['ac_cooling_energy'].sum() / df['total_energy_usage'].clip(lower=0.01).sum()) * 100

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Total Power Used", f"{tot_kwh:,.0f} kWh", "", "")
with c2: kpi_card("Avg Hourly Load", f"{avg_kwh:.1f} kWh", "", "")
with c3: kpi_card("Peak Demand", f"{peak_power_drain:.1f} kW", "", "", delta_good=False)
with c4: kpi_card("AC Cooling Share", f"{cooling_share:.1f}%", "Rises with outdoor temperature", "")
st.markdown("---")

t1, t2, t3, t4 = st.tabs([" Charts", " Benefits & Savings", " Smart Tips", " Test Changes"])

# ── Tab 1: Analytics ─────────────────────────────────────────────────────────
with t1:
    c_t1, c_t2 = st.columns([4, 1])
    with c_t2: show_fc = st.toggle(" Show Future Forecast", key="elec_fc")
    daily_bld = df.groupby([df["ts"].dt.date.rename("date"), "building_id"], as_index=False)["total_energy_usage"].sum()
    st.plotly_chart(make_daily_line(daily_bld, "date", "total_energy_usage", color_col="building_id", title="Daily kWh by Building", show_forecast=show_fc), width='stretch')

    col1, col2 = st.columns(2)
    b_df = df.copy()
    b_df["hour"] = b_df["ts"].dt.hour
    b_df["dow"]  = b_df["ts"].dt.day_name()
    pivot = b_df.pivot_table(values="total_energy_usage", index="dow", columns="hour", aggfunc="mean")
    with col1:
        st.plotly_chart(make_heatmap(pivot, "Avg Hourly Load Heatmap", "Reds"), width='stretch')
    with col2:
        st.plotly_chart(make_scatter(df.sample(min(1000, len(df))), "temperature", "ac_cooling_energy", "event_type", title="AC Load vs Outdoor Temperature"), width='stretch')

# ── Tab 2: Savings & Benefits ────────────────────────────────────────────────
with t2:
    section_header("Easy Ways to Save")
    col1, col2 = st.columns(2)
    with col1:
        insight_card("Adjust AC Temperatures Slightly", 
            "**Measure:** Increase cooling setpoint from 22°C to 24°C.<br>"
            "**If you do this:** HVAC energy consumption drops significantly.<br>"
            "** Est. Savings:** ~12% reduction in total AC load.", "#4fc3f7")
        insight_card("Turn off ACs at Night", 
            "**Measure:** Force HVAC shutdown in academic blocks post 9 PM.<br>"
            "**If you do this:** Eliminates ghost loads.<br>"
            "** Est. Savings:** 4-6% of total campus usage.", "#66bb6a")
    with col2:
        insight_card("Automatic Power Shutoffs", 
            "**Measure:** Auto-shutoff on all non-essential plugs at night.<br>"
            "**If you do this:** Mitigates wasted power from labs.<br>"
            "** Env Benefit:** High CO₂ reduction per campus block.", "#ffa726")

# ── Tab 3: AI Insights ───────────────────────────────────────────────────────
with t3:
    section_header("Domain-Specific AI Strategy")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        alert_card("Set `GROQ_API_KEY` in `.env` for AI insights.", "warning")
    else:
        if st.button("Generate Electricity Insights", type="primary"):
            with st.spinner("Analyzing electricity telemetry..."):
                st.markdown(analyze_electricity(api_key, df))

# ── Tab 4: Future Predictions ────────────────────────────────────────────────
with t4:
    section_header("Load Forecasting Modeler")
    st.markdown("Adjust the sliders below to see the simulated impact on next week's energy bill.")
    
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        temp_shift = st.slider("Forecasted Temp Shift (°C)", -5, 5, 2, help="Effect of a hotter/cooler week")
        hvac_upgrade = st.slider("Deployed AC Upgrades (%)", 0, 50, 0, help="Efficiency gain from new chillers")
        
    with pc2:
        base_hvac = df["ac_cooling_energy"].sum()
        base_plug = df["lights_and_sockets_energy"].sum()
        
        # Simple forecast model
        new_hvac = base_hvac * (1 + (temp_shift * 0.05)) * (1 - (hvac_upgrade/100))
        new_total = base_plug + new_hvac
        
        savings_kwh = tot_kwh - new_total
        savings_rs = savings_kwh * COST_PER_KWH
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: kpi_card("Predicted Energy", f"{new_total:,.0f} kWh", f"{'↗' if savings_kwh<0 else '↘'} {abs(savings_kwh):,.0f} kWh shift", "", delta_good=True)
        with c_p2: kpi_card("Bill Variance", f"₹ {savings_rs:,.0f}", "Net change in electricity bill", "", delta_good=(savings_rs > 0))
        
        chart_df = pd.DataFrame({
            "Source": ["Current Cooling", "Predicted Cooling", "Current Sockets", "Predicted Sockets"],
            "Load": [base_hvac, new_hvac, base_plug, base_plug],
            "Type": ["AC Cooling","AC Cooling","Lights & Sockets","Lights & Sockets"]
        })
        st.plotly_chart(px.bar(chart_df, x="Type", y="Load", color="Source", barmode="group", color_discrete_sequence=["#ef5350","#66bb6a","#4fc3f7","#26c6da"]), width='stretch')
