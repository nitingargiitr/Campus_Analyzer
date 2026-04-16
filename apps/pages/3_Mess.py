import sys, os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import pandas as pd

root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "src"))
load_dotenv(root_dir / ".env")

import pandas as pd
import streamlit as st
from apps.utils import check_data_loaded
import plotly.express as px

from campus_intel.config import get_paths
from campus_intel.db import connect_sqlite
from campus_intel.recommend import analyze_mess
from apps.utils import (
    inject_css, page_header, section_header, kpi_card,
    make_daily_line, make_heatmap, make_scatter, make_bar,
    insight_card, alert_card, PALETTE_QUAL, PLOTLY_THEME
)

st.set_page_config(page_title="Dining Analytics", layout="wide", page_icon="")
inject_css()

check_data_loaded("dataset_mess")
df = st.session_state["dataset_mess"]

if df.empty:
    st.warning("No data found.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
view_range = st.sidebar.radio("Time Window", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "All"])
messes     = st.sidebar.multiselect("Mess Halls", df["mess_id"].unique(), default=[df["mess_id"].unique()[0]])

if view_range == "Last 7 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=7)]
elif view_range == "Last 14 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=14)]
elif view_range == "Last 30 Days": df = df[df["ts"] >= df["ts"].max() - timedelta(days=30)]
df = df[df["mess_id"].isin(messes)]

# ── Header & KPIs ─────────────────────────────────────────────────────────────
page_header("", "Dining Intelligence", "Footfall patterns, wait times, menu ratings, and weather impact.")

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Avg Wait Time", f"{df['estimated_wait_min'].mean():.1f} min", "", "")
with c2: kpi_card("Peak Entries/Hr", f"{df['entries'].max()}", "", "")
with c3: kpi_card("Avg Student Rating", f"{df['student_rating'].mean():.2f}/5.0", "", "")
rain_wait = df[df["rain"] > 5]["estimated_wait_min"].mean()
with c4: kpi_card("Avg Wait in Rain", f"{rain_wait:.1f} min" if not pd.isna(rain_wait) else "N/A", "", "")
st.markdown("---")

t1, t2, t3, t4 = st.tabs([" Charts", " Benefits & Savings", " Smart Tips", " Test Changes"])

# ── Tab 1: Analytics ─────────────────────────────────────────────────────────
with t1:
    meal_df = df[df["meal_type"].isin(["Breakfast","Lunch","Dinner"])]
    c_t1, c_t2 = st.columns([4, 1])
    with c_t2: show_fc = st.toggle(" Show Future Forecast", key="mess_fc")
    daily = meal_df.groupby([meal_df["ts"].dt.date.rename("date"), "mess_id"], as_index=False)["entries"].sum().round(0)
    st.plotly_chart(make_daily_line(daily, "date", "entries", color_col="mess_id", title="Daily Visits by Mess", show_forecast=show_fc), width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        # Replaced box plots with grouped bar charts for simpler understanding
        bar_df = df.copy()
        bar_df["Rain Status"] = bar_df["rain"].apply(lambda x: "Raining" if x > 0 else "Clear")
        rain_agg = bar_df.groupby(["Rain Status", "meal_type"], as_index=False)["estimated_wait_min"].mean()
        fig_rain = px.bar(rain_agg, x="Rain Status", y="estimated_wait_min", color="meal_type", barmode="group",
                          title="Avg Wait Time vs Rain", color_discrete_sequence=PALETTE_QUAL, labels={"estimated_wait_min": "Avg Wait (min)"})
        fig_rain.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_rain, width='stretch')
        
    with col2:
        rating_agg = df.groupby("menu_served", as_index=False)["student_rating"].mean().sort_values("student_rating", ascending=False)
        fig_menu = px.bar(rating_agg, x="menu_served", y="student_rating", color="menu_served", 
                          title="Avg Menu Ratings", color_discrete_sequence=PALETTE_QUAL, labels={"student_rating": "Avg Rating"})
        fig_menu.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_menu, width='stretch')

# ── Tab 2: Savings & Benefits ────────────────────────────────────────────────
with t2:
    section_header("Ways to Improve the Mess")
    col1, col2 = st.columns(2)
    with col1:
        insight_card("Grab-and-Go Meals on Rainy Days", 
            "**Measure:** Stock grab-and-go options at academic blocks when rain > 5mm.<br>"
            "**If you do this:** Reduces central mess load by 15%.<br>"
            "** Benefit:** Prevents queue times exceeding 20+ minutes.", "#4fc3f7")
    with col2:
        insight_card("Different Lunch Times for Students", 
            "**Measure:** Shift first-year lunch hour forward by 30 mins.<br>"
            "**If you do this:** Flattens the midday peak.<br>"
            "** Benefit:** Reduces staff stress, decreases food waste via better batch cooking.", "#66bb6a")

# ── Tab 3: AI Insights ───────────────────────────────────────────────────────
with t3:
    section_header("AI Dining Strategist")
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key: alert_card("Set `GROQ_API_KEY` in `.env` for AI insights.", "warning")
    else:
        if st.button("Generate Mess Insights", type="primary"):
            with st.spinner("Analyzing mess data..."):
                st.markdown(analyze_mess(api_key, df))

# ── Tab 4: Future Predictions ────────────────────────────────────────────────
with t4:
    section_header("Queue Wait Simulator")
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        capacity_inc = st.slider("Increase Server Lines (+N)", 0, 10, 0)
        stagger_pct  = st.slider("Spread Students over Time (%)", 0, 50, 0)
        
    with pc2:
        base_wait = df["estimated_wait_min"].mean()
        peak_wait = df["estimated_wait_min"].max()
        
        # Simple queueing mock: doubling servers halves wait. Staggering lowers peak.
        new_avg = base_wait * (1 - (stagger_pct/200)) / (1 + (capacity_inc*0.1))
        new_peak= peak_wait * (1 - (stagger_pct/100)) / (1 + (capacity_inc*0.1))
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: kpi_card("Predicted Avg Wait", f"{new_avg:.1f} m", f"{(new_avg-base_wait):.1f} min", "", delta_good=new_avg<base_wait)
        with c_p2: kpi_card("Predicted Peak Wait", f"{new_peak:.1f} m", f"{(new_peak-peak_wait):.1f} min", "", delta_good=new_peak<peak_wait)
        
        chart_df = pd.DataFrame({"Metric":["Avg", "Avg", "Peak", "Peak"], "Val":[base_wait, new_avg, peak_wait, new_peak], "Type":["Baseline","Predicted","Baseline","Predicted"]})
        st.plotly_chart(px.bar(chart_df, x="Metric", y="Val", color="Type", barmode="group", color_discrete_sequence=["#ef5350","#4fc3f7"]), width='stretch')
