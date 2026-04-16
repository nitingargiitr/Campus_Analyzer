"""Shared design utilities for Smart Campus Intelligence dashboard."""
from __future__ import annotations
import os, sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ── Constants ──────────────────────────────────────────────────────────────────
COST_PER_KWH   = 8.0        # ₹ per kWh (Indian campus tariff)
CO2_PER_KWH    = 0.82       # kg CO₂ per kWh (India grid factor)
SOLAR_BENCH    = 0.03       # ₹/kWh solar benchmark for savings
COLORS = {
    "primary":   "#4fc3f7",
    "success":   "#66bb6a",
    "warning":   "#ffa726",
    "danger":    "#ef5350",
    "purple":    "#ab47bc",
    "teal":      "#26c6da",
    "card_bg":   "#161b22",
    "card_border":"#30363d",
    "bg":        "#0d1117",
    "text":      "#e6edf3",
    "muted":     "#8b949e",
}

PLOTLY_THEME = dict(
    plot_bgcolor  = "#161b22",
    paper_bgcolor = "#0d1117",
    font          = dict(color="#e6edf3", family="Inter, sans-serif"),
    xaxis         = dict(gridcolor="#21262d", tickcolor="#8b949e", linecolor="#30363d"),
    yaxis         = dict(gridcolor="#21262d", tickcolor="#8b949e", linecolor="#30363d"),
    legend        = dict(bgcolor="rgba(22,27,34,0.8)", bordercolor="#30363d", borderwidth=1),
    hovermode     = "x unified",
    hoverlabel    = dict(bgcolor="#161b22", bordercolor="#4fc3f7", font_color="#e6edf3"),
    margin        = dict(t=50, b=40, l=40, r=20),
)

PALETTE_QUAL   = ["#4fc3f7","#66bb6a","#ffa726","#ab47bc","#26c6da","#ef5350","#fff176","#80cbc4"]
PALETTE_ENERGY = "Blues"
PALETTE_HEAT   = "RdYlGn_r"

# ── Global CSS ─────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: linear-gradient(-45deg, #0b0f1a, #0f172a, #020617, #0b0f1a) !important;
    background-size: 400% 400% !important;
    animation: gradientBG 15s ease infinite !important;
    color: #e6edf3 !important;
}

@keyframes gradientBG {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

*, *::before, *::after { box-sizing: border-box; }

[data-testid="stAppViewContainer"] {
    background: transparent !important;
}

section[data-testid="stSidebar"] {
    background: rgba(10,15,28,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(20px) !important;
}

[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSelectbox label { color: #8b949e !important; font-size: 0.78rem !important; }

h1, h2, h3, h4 { color: #e6edf3 !important; font-family: 'Inter', sans-serif !important; }
p, span, li, label { color: #c9d1d9 !important; }
b, strong { font-weight: 700 !important; color: #4fc3f7 !important; }

/* KPI Card Glassmorphism */
.kpi-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 20px;
    border-radius: 18px;
    backdrop-filter: blur(14px);
    transition: all 0.3s ease;
    position: relative;
    height: 100%;
}
.kpi-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 0 25px rgba(59,130,246,0.35);
    border: 1px solid rgba(59,130,246,0.6);
}

/* Tabs */
div[data-baseweb="tab-list"] {
    background: #161b22 !important;
    border-radius: 8px !important;
    border: 1px solid #30363d !important;
    padding: 4px !important;
}
div[data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 6px !important;
    color: #8b949e !important;
}
div[data-baseweb="tab"][aria-selected="true"] {
    background: #21262d !important;
    color: #4fc3f7 !important;
    border-bottom: 2px solid #4fc3f7 !important;
}

/* Metrics */
[data-testid="stMetric"] { background: #161b22; border:1px solid #30363d; border-radius:10px; padding:16px; }
[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #e6edf3 !important; font-weight: 700 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1c4a8a 0%, #2563eb 100%) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; padding: 10px 24px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 15px rgba(79,195,247,0.3) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0c7a4a 0%, #16a34a 100%) !important;
}

/* Expanders */
.streamlit-expanderHeader { background: #161b22 !important; border-radius: 8px !important; color: #e6edf3 !important; }
.streamlit-expanderContent { background: #0d1117 !important; border: 1px solid #21262d !important; }

/* Sliders */
[data-testid="stSlider"] .stSlider > div > div { background: #21262d !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] { background: #4fc3f7 !important; border-color: #4fc3f7 !important; }

/* File uploader */
[data-testid="stFileUploader"] {
    background: #161b22 !important; border: 2px dashed #30363d !important;
    border-radius: 10px !important;
}

/* Dividers */
hr { border-color: #21262d !important; }

/* Success/warning/error boxes */
.stSuccess { background: rgba(102,187,106,0.1) !important; border-left: 4px solid #66bb6a !important; }
.stWarning { background: rgba(255,167,38,0.1) !important; border-left: 4px solid #ffa726 !important; }
.stError   { background: rgba(239,83,80,0.1) !important; border-left: 4px solid #ef5350 !important; }

/* Sidebar nav text */
.st-emotion-cache-eczf16, [data-testid="stSidebarNav"] a { color: #8b949e !important; }
.st-emotion-cache-eczf16:hover, [data-testid="stSidebarNav"] a:hover { color: #4fc3f7 !important; }
</style>
"""

# ── Reusable Components ────────────────────────────────────────────────────────

def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div style="padding:8px 0 4px 0; border-bottom:1px solid #21262d; margin-bottom:24px;">
        <h1 style="font-size:1.9rem; margin:0; display:flex; align-items:center; gap:12px;">
            <span style="font-size:2rem;">{icon}</span> {title}
        </h1>
        {f'<p style="color:#8b949e; margin:6px 0 0 0; font-size:0.9rem;">{subtitle}</p>' if subtitle else ""}
    </div>""", unsafe_allow_html=True)

def section_header(title: str, color: str = "#4fc3f7"):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:24px 0 12px 0;">
        <div style="width:4px;height:24px;background:{color};border-radius:2px;"></div>
        <h3 style="margin:0;font-size:1.1rem;font-weight:600;color:#e6edf3;">{title}</h3>
    </div>""", unsafe_allow_html=True)

def kpi_card(label: str, value: str, delta: str = "", icon: str = "", color: str = "#4fc3f7", delta_good: bool = True):
    delta_color = "#22c55e" if delta_good else "#ef4444"
    delta_html  = f'<div style="font-size:0.78rem;color:{delta_color};margin-top:4px; font-weight: 500;">{delta}</div>' if delta else ""
    html_content = f"""
<div class="kpi-card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
            <div style="font-size:0.78rem;color:#8b949e;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">{label}</div>
            <div style="font-size:1.8rem;font-weight:700;color:{color};margin-top:6px;line-height:1;">{value}</div>{delta_html}
        </div>
        <div style="font-size:1.8rem;opacity:0.7;">{icon}</div>
    </div>
</div>
"""
    html_content = html_content.replace('\\n', '')
    st.markdown(html_content, unsafe_allow_html=True)

import re

def insight_card(title: str, body: str, color: str = "#4fc3f7"):
    # Fix markdown double asterisks correctly parsing inside inner HTML blocks
    parsed_body = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', body)
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-left:4px solid {color};
                border-radius:12px; padding:18px 20px; margin:8px 0; backdrop-filter: blur(14px);">
        <div style="font-weight:600;color:{color};margin-bottom:6px;font-size:1.05rem;"> {title}</div>
        <div style="color:#e2e8f0;font-size:0.9rem;line-height:1.6;">{parsed_body}</div>
    </div>""", unsafe_allow_html=True)

def alert_card(msg: str, kind: str = "info"):
    colors = {"info":"#4fc3f7","success":"#66bb6a","warning":"#ffa726","danger":"#ef5350"}
    icons  = {"info":"","success":"","warning":"⚠","danger":""}
    c = colors.get(kind,"#4fc3f7")
    st.markdown(f"""
    <div style="background:rgba(22,27,34,0.8);border-left:4px solid {c};
                border-radius:0 8px 8px 0;padding:12px 16px;margin:8px 0;">
        <span style="color:{c};font-weight:600;">{icons.get(kind,'')} </span>
        <span style="color:#c9d1d9;font-size:0.9rem;">{msg}</span>
    </div>""", unsafe_allow_html=True)

def auto_load_data():
    """Automatically loads simulation data from SQLite into session state."""
    # Marking that we've attempted to load to avoid infinite loops on fatal errors
    if "data_load_attempted" in st.session_state and st.session_state["data_load_attempted"]:
        return
    
    st.session_state["data_load_attempted"] = True
    
    try:
        from campus_intel.config import get_paths
        from campus_intel.db import connect_sqlite
        
        # Calculate root_dir based on apps/ location
        root_dir = Path(__file__).resolve().parents[1]
        paths = get_paths(root_dir)
        
        if not paths.db_path.exists():
            st.session_state["load_error"] = f"Database not found at: {paths.db_path}"
            return # Let the pages handle the missing data gracefully or show error later

        conn = connect_sqlite(paths.db_path)
        
        datasets = {
            "dataset_electricity": "SELECT eu.*, b.building_name, b.building_type FROM electricity_usage eu LEFT JOIN buildings b USING(building_id)",
            "dataset_mess": "SELECT * FROM mess_footfall",
            "dataset_transport": "SELECT * FROM shuttle_transport",
            "dataset_wifi": "SELECT wu.*, a.building_id, b.building_name FROM wifi_usage wu LEFT JOIN wifi_aps a USING(ap_id) LEFT JOIN buildings b USING(building_id)",
            "dataset_library": "SELECT * FROM library_occupancy"
        }
        
        for key, query in datasets.items():
            if key not in st.session_state:
                df = pd.read_sql_query(query, conn)
                if not df.empty:
                    df["ts"] = pd.to_datetime(df["ts"], utc=True)
                st.session_state[key] = df
        
        conn.close()
        st.session_state["data_loaded"] = True
        
    except Exception as e:
        # Silent fail or log - we don't want to crash the whole UI if one import fails
        pass

def check_data_loaded(domain_key: str):
    """Checks if data is loaded, and if not, attempts an auto-load."""
    if domain_key not in st.session_state:
        auto_load_data()
        
    # If still not loaded after attempt, show error
    if domain_key not in st.session_state:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-left:4px solid #ef5350;border-radius:8px;padding:30px;text-align:center;margin-top:20px;">
            <h2 style="color:#e6edf3;margin-top:0;">{domain_key.split('_')[-1].title()} Data Unavailable</h2>
            <p style="color:#8b949e;font-size:1.0rem;">The simulation database could not be found or loaded automatically.</p>
            <p style="color:#c9d1d9;margin-bottom:0;">Please ensure you have run the simulation pipeline: <code>python scripts/run_pipeline.py</code></p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

def apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=14, color="#e6edf3"), x=0))
    fig.update_layout(**PLOTLY_THEME)
    return fig

def make_daily_line(df, x, y, color_col=None, title="", show_forecast=False):
    df[x] = pd.to_datetime(df[x])
    fig = px.line(df, x=x, y=y, color=color_col, color_discrete_sequence=PALETTE_QUAL)
    fig.update_traces(line=dict(width=2.5), mode="lines")
    
    if show_forecast and len(df) > 3:
        if color_col:
            for i, cat in enumerate(df[color_col].unique()):
                cdf = df[df[color_col] == cat].sort_values(x)
                if len(cdf) < 2: continue
                last_dt = cdf[x].iloc[-1]
                pred_val = cdf[y].tail(7).mean()
                future_dates = [last_dt + pd.Timedelta(days=j) for j in range(1, 8)]
                fig.add_trace(go.Scatter(
                    x=[last_dt] + future_dates, y=[cdf[y].iloc[-1]] + [pred_val]*7,
                    name=f"{cat} (Forecast)", line=dict(color=PALETTE_QUAL[i % len(PALETTE_QUAL)], dash="dash", width=2.5),
                    mode="lines", showlegend=False, hoverinfo="skip"
                ))
        else:
            df = df.sort_values(x)
            last_dt = df[x].iloc[-1]
            pred_val = df[y].tail(7).mean()
            future_dates = [last_dt + pd.Timedelta(days=j) for j in range(1, 8)]
            fig.add_trace(go.Scatter(
                x=[last_dt] + future_dates, y=[df[y].iloc[-1]] + [pred_val]*7,
                name="Forecast", line=dict(color=PALETTE_QUAL[0], dash="dash", width=2.5),
                mode="lines"
            ))
            
    fig.update_layout(hovermode="x unified", title=dict(text=title, font=dict(size=14, color="#e6edf3"), x=0))
    fig.update_layout(**PLOTLY_THEME)
    return fig

def make_heatmap(pivot, title="", colorscale="PuBu"):
    fig = px.imshow(pivot, color_continuous_scale=colorscale,
                    labels=dict(x="Hour of Day", y="", color="Value"), aspect="auto")
    fig.update_traces(xgap=2, ygap=2)
    return apply_theme(fig, title)

def make_bar(df, x, y, color_col=None, title="", color=None, colorscale=None):
    if colorscale:
        fig = px.bar(df, x=x, y=y, color=y, color_continuous_scale=colorscale,
                     title=title)
    elif color_col:
        fig = px.bar(df, x=x, y=y, color=color_col, title=title,
                     color_discrete_sequence=PALETTE_QUAL)
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                     color_discrete_sequence=[color or COLORS["primary"]])
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    return apply_theme(fig, "")

def make_scatter(df, x, y, color=None, size=None, trendline=True, title=""):
    fig = px.scatter(df, x=x, y=y, color=color, size=size,
                     trendline="ols" if trendline else None,
                     opacity=0.45,
                     color_discrete_sequence=PALETTE_QUAL)
    fig.update_traces(marker=dict(size=6, line=dict(width=0)))
    if trendline:
        fig.update_traces(showlegend=False, selector=dict(mode='lines')) # Hide equation traces from legend
    return apply_theme(fig, title)
