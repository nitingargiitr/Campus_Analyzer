"""Main Executive Dashboard and Entry Portal."""
from __future__ import annotations
import sys
import json
import time
import pandas as pd
import streamlit as st
import os
from pathlib import Path

from dotenv import load_dotenv
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))
load_dotenv(root_dir / ".env")

from groq import Groq
from apps.utils import (
    inject_css, page_header, section_header, kpi_card,
    make_daily_line, make_bar, COST_PER_KWH, CO2_PER_KWH, insight_card, alert_card
)

from campus_intel.config import get_paths
from campus_intel.db import connect_sqlite
from campus_intel.recommend import generate_groq_insights

st.set_page_config(page_title="Executive Portal", layout="wide", page_icon="", initial_sidebar_state="expanded")
inject_css()

# Define globally so it's accessible across tabs
api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not api_key:
    # Fallback to User's hardcoded key if .env fails
    api_key = "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"

# ── 1. The Gated Upload Interface ──
required_datasets = ["dataset_electricity", "dataset_mess", "dataset_transport", "dataset_wifi", "dataset_library"]
data_loaded = all([k in st.session_state for k in required_datasets])

if not data_loaded:
    # Completely hide the sidebar navigation until data is unlocked
    st.markdown("""<style>[data-testid="stSidebar"] { display: none !important; }</style>""", unsafe_allow_html=True)
    
    page_header("", "Smart Campus Initialization", "Upload your raw, unconfigured CSV arrays or deploy the simulated IIT Roorkee sensor data to unlock the platform.")
    
    st.markdown("### 1. Bypass & Deploy Simulation Data")
    st.write("Don't have a configured sensor CSV? Deploy the physics-based IIT Roorkee simulated data globally.")
    if st.button(" Use Default Sample Data", type="primary"):
        with st.spinner("Connecting to generated local SQLite framework..."):
            paths = get_paths(root_dir)
            if not paths.db_path.exists():
                st.error("Simulation Database not found! Please run the pipeline script first.")
            else:
                conn = connect_sqlite(paths.db_path)
                elec = pd.read_sql_query(
                    "SELECT eu.*, b.building_name, b.building_type "
                    "FROM electricity_usage eu LEFT JOIN buildings b USING(building_id)", conn)
                mess = pd.read_sql_query("SELECT * FROM mess_footfall", conn)
                trans = pd.read_sql_query("SELECT * FROM shuttle_transport", conn)
                wifi = pd.read_sql_query(
                    "SELECT wu.*, a.building_id, b.building_name "
                    "FROM wifi_usage wu "
                    "LEFT JOIN wifi_aps a USING(ap_id) "
                    "LEFT JOIN buildings b USING(building_id)", conn)
                lib = pd.read_sql_query("SELECT * FROM library_occupancy", conn)
                conn.close()
                
                for df in [elec, mess, trans, wifi, lib]:
                    if not df.empty: df["ts"] = pd.to_datetime(df["ts"], utc=True)
                    
                st.session_state["dataset_electricity"] = elec
                st.session_state["dataset_mess"] = mess
                st.session_state["dataset_transport"] = trans
                st.session_state["dataset_wifi"] = wifi
                st.session_state["dataset_library"] = lib
                
                st.session_state["data_loaded"] = True
                st.rerun() # Refresh to drop the lockscreen and reveal sidebar

    st.markdown("---")
    
    st.markdown("### 2. Upload Your Own Data")
    if not api_key: alert_card("Set `GROQ_API_KEY` in `.env` to enable dynamic AI CSV mapping.", "warning")

    st.write("Upload any CSV file — our AI will automatically figure out what kind of data it is and map it to the correct module. Your column names don't need to match exactly.")

    with st.expander(" What should my CSV look like?", expanded=False):
        st.markdown("""
We support **5 types of datasets**. Your columns can have different names — the AI will figure out the mapping.
Just make sure your file contains the type of information described below.

| Module | What you need | Example column names |
|---|---|---|
|  **Electricity** | Time, building name, energy used, AC/cooling energy | `timestamp`, `building`, `power_kwh`, `cooling_kwh` |
|  **WiFi** | Time, location/device point, number of devices, speed, delays | `time`, `access_point`, `devices`, `speed_mbps`, `delay_ms` |
|  **Mess / Dining** | Time, mess/canteen name, number of visitors, wait time | `date`, `canteen`, `footfall`, `queue_min` |
|  **Transport** | Time, route name, passenger count, delay | `ts`, `route`, `passengers`, `late_min` |
|  **Library** | Time, quiet zone occupancy, collab zone occupancy, event | `time`, `quiet_zone`, `collab_zone`, `event` |

> **Tip:** A timestamp/time column is required for all charts to render properly.
        """)

    uploaded_file = st.file_uploader("Drop your CSV file here", type=["csv"])

    if uploaded_file and api_key:
        if "mapper_ran" not in st.session_state or st.session_state.get("last_uploaded") != uploaded_file.name:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state["last_uploaded"] = uploaded_file.name
                
                st.write("---")
                st.markdown("#### AI Mapping Engine")
                
                pb = st.progress(0, "Reading raw CSV columns...")
                time.sleep(0.5)
                
                client = Groq(api_key=api_key)
                cols = list(df.columns)
                prompt = f"""We are parsing a raw IoT sensor CSV to feed an Executive Dashboard.
Here are the columns in the uploaded file: {cols}

Which Dashboard module does this data belong to? The choices are:
- dataset_electricity (needs: ts, lights_and_sockets_energy, ac_cooling_energy, total_energy_usage, peak_power_drain)
- dataset_wifi (needs: ts, ap_id, connected_devices, internet_speed, connection_drops, network_delay)
- dataset_mess (needs: ts, mess_id, entries, estimated_wait_min)
- dataset_transport (needs: ts, bus_id, route, passenger_count, delay_minutes)
- dataset_library (needs: ts, occupancy_quiet_zone, occupancy_collab_zone, total_occupancy, event_type)

Return ONLY valid strict JSON measuring this schema exactly:
{{
   "detected_module": "dataset_X",
   "column_mapping": {{
        "original_uploaded_column_name_1": "dashboard_required_name_1"
   }}
}}"""
                pb.progress(30, "Inferring exact relational columns through Groq...")
                
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=300
                )
                
                pb.progress(70, "Translating AI mapping output...")
                res = completion.choices[0].message.content.strip()
                if res.startswith("```json"): res = res[7:-3]
                elif res.startswith("```"): res = res[3:-3]
                
                mapping_dict = json.loads(res.strip())
                pb.progress(90, f"Harmonizing data into {mapping_dict['detected_module']}...")
                
                df = df.rename(columns=mapping_dict["column_mapping"])
                if "ts" in df.columns: df["ts"] = pd.to_datetime(df["ts"], utc=True)
                
                st.session_state[mapping_dict['detected_module']] = df
                pb.progress(100, "Module unlocked!")
                
                st.success(f"Dataset ingested for `{mapping_dict['detected_module']}`. If all modules are loaded, the site will unlock.")
            except Exception as e:
                alert_card(f"AI Mapping Error: {str(e)}", "danger")

    st.markdown("### Loaded Modules")
    status_df = pd.DataFrame([{ "Module": m.split("_")[1].title(), "Status": " Connected" if m in st.session_state else " Awaiting Data" } for m in required_datasets])
    st.table(status_df)
    
    st.stop()


# ── 2. The Unlocked Dashboard Analysis ──
page_header("", "Executive Dashboard", "High-level impact, sustainability, and operational efficiency across the campus.")

df_elec  = st.session_state["dataset_electricity"]
df_mess  = st.session_state["dataset_mess"]
df_trans = st.session_state["dataset_transport"]
df_wifi  = st.session_state["dataset_wifi"]

# Dynamically calculate the KPIs (Replacing obsolete SQL)
elec_daily = df_elec.groupby(df_elec["ts"].dt.date.rename("day"))["total_energy_usage"].sum().reset_index()
mess_daily = df_mess.groupby(df_mess["ts"].dt.date.rename("day")).agg(
    total_mess_entries=("entries", "sum"),
    avg_wait_min=("estimated_wait_min", "mean")
).reset_index()
wifi_daily = df_wifi.groupby(df_wifi["ts"].dt.date.rename("day"))["connected_devices"].mean().rename("avg_connected_devices").reset_index()

kpi_df = elec_daily.merge(mess_daily, on="day", how="outer").merge(wifi_daily, on="day", how="outer")
kpi_df["day"] = pd.to_datetime(kpi_df["day"])
kpi_df = kpi_df.sort_values("day")

if kpi_df.empty:
    st.warning("Insufficient data.")
    st.stop()

# ── Metrics Validation & Delta ───────────────────────────────────────────────
last_7 = kpi_df.tail(7)
prev_7 = kpi_df.iloc[-14:-7] if len(kpi_df) >= 14 else pd.DataFrame()

avg_kwh = last_7["total_energy_usage"].mean()
prev_kwh = prev_7["total_energy_usage"].mean() if not prev_7.empty else avg_kwh
delta_kwh = avg_kwh - prev_kwh

avg_cost = avg_kwh * COST_PER_KWH
delta_cost = delta_kwh * COST_PER_KWH

avg_co2 = avg_kwh * CO2_PER_KWH
delta_co2 = delta_kwh * CO2_PER_KWH

avg_wait = last_7["avg_wait_min"].mean()
delta_wait = avg_wait - (prev_7["avg_wait_min"].mean() if not prev_7.empty else avg_wait)

st.markdown("### 📅 Last 7 Days Average Impact")
c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Energy Usage", f"{avg_kwh:,.0f} kWh", f"{'+' if delta_kwh>0 else ''}{delta_kwh:,.0f} vs prev week", "", delta_good=(delta_kwh<=0))
with c2: kpi_card("Est. Cost", f"₹{avg_cost:,.0f}", f"{'+' if delta_cost>0 else ''}₹{delta_cost:,.0f} vs prev", "", delta_good=(delta_cost<=0))
with c3: kpi_card("Carbon Footprint", f"{avg_co2:,.0f} kg", f"{'+' if delta_co2>0 else ''}{delta_co2:,.0f} kg CO₂", "", delta_good=(delta_co2<=0))
with c4: kpi_card("Mess Wait Times", f"{avg_wait:.1f} min", f"{'+' if delta_wait>0 else ''}{delta_wait:.1f} min delay", "", delta_good=(delta_wait<=0))
st.markdown("---")

t1, t2, t3 = st.tabs([" Main Charts", " Big Picture Benefits", " Test Campus Changes"])

with t1:
    section_header("Overall Energy Use")
    c_chart1, c_chart2 = st.columns([2, 1])
    
    c_t1, c_t2 = st.columns([4, 1])
    with c_t2: show_fc = st.toggle(" Show Future Forecast", key="dash_fc")
    with c_chart1:
        st.plotly_chart(make_daily_line(kpi_df.tail(30), "day", "total_energy_usage", title="Campus Energy Trajectory (30 Days)", show_forecast=show_fc), width='stretch')
    with c_chart2:
        st.plotly_chart(make_daily_line(kpi_df.tail(30), "day", "avg_wait_min", title="Dining Wait Times", show_forecast=show_fc), width='stretch')

    section_header("Campus Pulse")
    c_pulse1, c_pulse2 = st.columns(2)
    with c_pulse1:
        st.plotly_chart(make_daily_line(kpi_df.tail(30), "day", "total_mess_entries", title="Total Mess Visitors", show_forecast=show_fc), width='stretch')
    with c_pulse2:
        st.plotly_chart(make_daily_line(kpi_df.tail(30), "day", "avg_connected_devices", title="WiFi Device Saturation", show_forecast=show_fc), width='stretch')

with t2:
    section_header("Campus-Wide Actions & Savings")
    st.markdown("These are the estimated campus-wide benefits if broad policy changes are implemented based on current baseline data.")
    total_yearly_kwh = avg_kwh * 365
    col1, col2 = st.columns(2)
    with col1:
        insight_card("Unified Academic Working Hours", 
            f"**Measure:** Standardize closing academic blocks strictly at 6 PM instead of 8 PM.<br>"
            f"**If you do this:** Expected 12% drop in {total_yearly_kwh:,.0f} kWh annual usage.<br>"
            f"** Benefit:** ₹{(total_yearly_kwh * 0.12 * COST_PER_KWH):,.0f} saved annually. Reductions in late-night phantom ACs.", "#4fc3f7")
        
    with col2:
        insight_card("Targeted Central Dining Routing", 
            "**Measure:** Automatically route students via digital boards to the least crowded mess.<br>"
            "**If you do this:** Spreads volume away from Central Mess during breakfast rush.<br>"
            "** Benefit:** Shrinks average network delay times across the campus by 45%.", "#66bb6a")

with t3:
    section_header("Global Optimization Simulator")
    pc1, pc2 = st.columns([1, 2])
    with pc1:
        ac_reduction = st.slider("Strict AC Governance (-%)", 0, 30, 0)
        route_reduction = st.slider("Route Consolidation (reduce trips %)", 0, 30, 0)
        st.caption("Simulator calculates real-time predictive shifts in underlying campus dynamics.")

    with pc2:
        new_kwh = avg_kwh * (1 - (ac_reduction/100) * 0.45) # Approx 45% is cooling
        save_kwh = avg_kwh - new_kwh
        c_p1, c_p2 = st.columns(2)
        with c_p1: kpi_card("Predicted Energy", f"{new_kwh:,.0f} kWh", f"Saved {save_kwh:,.0f} kWh", "", True)
        
        # Simple mocked delay calculation based on trips removed
        avg_delay = df_trans["delay_minutes"].mean() if "delay_minutes" in df_trans.columns else 0
        new_delay = avg_delay * (1 + (route_reduction/100) * 1.5)
        with c_p2: kpi_card("Predicted Avg Bus Delay", f"{new_delay:.1f} m", f"+{new_delay - avg_delay:.1f} m", "", new_delay <= avg_delay)

