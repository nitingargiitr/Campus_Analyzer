import sys, os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))
load_dotenv(root_dir / ".env")

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from campus_intel.recommend import analyze_library
from apps.utils import (
    inject_css, page_header, section_header, kpi_card,
    make_daily_line, make_heatmap, insight_card, alert_card, check_data_loaded
)

st.set_page_config(page_title="Library Analytics", layout="wide", page_icon="")
inject_css()

check_data_loaded("dataset_library")
df = st.session_state["dataset_library"]

if df.empty:
    st.warning("No data found.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
view_range = st.sidebar.radio("Time Window", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "All"])

if view_range == "Last 7 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=7)]
elif view_range == "Last 14 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=14)]
elif view_range == "Last 30 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=30)]

# ── Header & KPIs ─────────────────────────────────────────────────────────────
page_header("", "Library Intelligence", "Zone utilization, crowding, and event-based demand shifts.")

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Avg Quiet Zone", f"{df['occupancy_quiet_zone'].mean():.0f}", "", "")
with c2: kpi_card("Avg Collab Zone", f"{df['occupancy_collab_zone'].mean():.0f}", "", "")
with c3: kpi_card("Peak Total Occupancy", f"{df['total_occupancy'].max()}", "", "")
exam_occ = df[df["event_type"] == "exam_week"]["total_occupancy"].mean()
with c4: kpi_card("Exam Week Avg", f"{exam_occ:.0f}" if not pd.isna(exam_occ) else "N/A", "", "")
st.markdown("---")

t1, t2, t3, t4 = st.tabs([" Charts", " Benefits & Savings", " Smart Tips", " Test Changes"])

# ── Tab 1: Analytics ─────────────────────────────────────────────────────────
with t1:
    daily = df.groupby(df["ts"].dt.date.rename("date"), as_index=False)["total_occupancy"].mean().round(0)
    daily["date"] = pd.to_datetime(daily["date"])
    from apps.utils import make_daily_line
    c_t1, c_t2 = st.columns([4, 1])
    with c_t2: show_fc_lib = st.toggle(" Show Future Forecast", key="lib_fc")
    st.plotly_chart(make_daily_line(daily, "date", "total_occupancy", title="Daily Average Library Visitors", show_forecast=show_fc_lib), width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        b_df = df.copy()
        b_df["hour"] = b_df["ts"].dt.hour
        b_df["dow"]  = b_df["ts"].dt.day_name()
        pivot = b_df.pivot_table(values="total_occupancy", index="dow", columns="hour", aggfunc="mean")
        st.plotly_chart(make_heatmap(pivot, "Hourly Heatmap", "Blues"), width='stretch')
    with col2:
        ev = df.groupby("event_type", as_index=False)["total_occupancy"].mean()
        fig_bar = px.bar(ev, x="event_type", y="total_occupancy", color="event_type", title="Demand By Event Type")
        fig_bar.update_layout(plot_bgcolor="#161b22", paper_bgcolor="#0d1117", font_color="#e6edf3")
        st.plotly_chart(fig_bar, width='stretch')

# ── Tab 2: Savings & Benefits ────────────────────────────────────────────────
with t2:
    section_header("Library Savings")
    col1, col2 = st.columns(2)
    with col1:
        insight_card("Smart AC Control based on Crowd", 
            "**Measure:** Sync AC zones directly to headcount density rather than fixed timings.<br>"
            "**If you do this:** Shuts off extreme cooling in empty Collab zones.<br>"
            "** Benefit:** Extrapolated 10-15% kWh savings for the Library Building.", "#4fc3f7")
    with col2:
        insight_card("Extra Study Rooms during Exams", 
            "**Measure:** Open empty lecture halls during exam week as 'overflow' quiet study zones.<br>"
            "**If you do this:** Distributes massive 3x demand spikes away from central library.<br>"
            "** Benefit:** Eliminates student seating frustration and wifi degradation.", "#66bb6a")

# ── Tab 3: AI Insights ───────────────────────────────────────────────────────
with t3:
    section_header("AI Library Strategies")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key: alert_card("Set `GROQ_API_KEY` in `.env` for AI insights.", "warning")
    else:
        if st.button("Generate Library Insights", type="primary"):
            with st.spinner("Analyzing library data..."):
                st.markdown(analyze_library(api_key, df))

# ── Tab 4: Future Predictions ────────────────────────────────────────────────
with t4:
    section_header("Crowd Simulator")
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        student_admissions = st.slider("Increase Overall Student Body (%)", 0, 50, 10)
        collab_convert = st.slider("Convert Quiet Space to Collab (%)", 0, 100, 0)
        
    with pc2:
        base_total = df["total_occupancy"].mean()
        
        new_quiet = df["occupancy_quiet_zone"].mean() * (1 + student_admissions/100) * (1 - collab_convert/100)
        new_collab = df["occupancy_collab_zone"].mean() * (1 + student_admissions/100) + (df["occupancy_quiet_zone"].mean() * (collab_convert/100))
        new_total = new_quiet + new_collab
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: kpi_card("Predicted Base Load", f"{new_total:.0f} seats", f"{'+' if new_total>base_total else ''}{new_total-base_total:.0f}", "", new_total<=800)
        with c_p2:
            alert_card(f"Max library capacity is 900. {'Warning! Capacity Breach.' if new_total > 850 else 'Safe Capacity.'}", "danger" if new_total>850 else "success")
        
        chart_df = pd.DataFrame({"Zone":["Quiet", "Collab"], "Current":[df["occupancy_quiet_zone"].mean(), df["occupancy_collab_zone"].mean()], "Predicted":[new_quiet, new_collab]})
        st.plotly_chart(px.bar(chart_df.melt(id_vars="Zone"), x="Zone", y="value", color="variable", barmode="group"), width='stretch')
