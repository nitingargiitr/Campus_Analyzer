from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

try:
    from groq import Groq
except ImportError:
    Groq = None


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_recommendations(
    electricity_usage: pd.DataFrame,
    wifi_usage: pd.DataFrame,
    mess_footfall: pd.DataFrame,
    anomalies: pd.DataFrame,
    forecast_elec_daily: pd.DataFrame,
    peak_mess_forecast: pd.DataFrame,
) -> pd.DataFrame:
    recs: list[dict] = []
    recs.append({
        "rec_id": str(uuid.uuid4()),
        "created_ts": _now(),
        "category": "system",
        "target_type": "campus",
        "target_id": "all",
        "time_window": "Always",
        "reason": "Structured recommendations superseded by AI Insights panel on each dashboard page.",
        "confidence": 1.0,
        "expected_impact": "See per-view AI analysis sections.",
        "priority": 1,
    })
    out = pd.DataFrame(recs)
    out["priority"] = out["priority"].astype(int)
    out["confidence"] = out["confidence"].astype(float).clip(0.0, 1.0)
    return out


def _call_groq(api_key: str, prompt: str) -> str:
    if not Groq or not api_key:
        return " Groq package not installed or API key not configured in `.env`."
    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f" Groq API Error: {str(e)}"


def _safe(df: pd.DataFrame, col: str, agg="mean", fallback="N/A"):
    """Safely aggregate a column that might not exist."""
    if col not in df.columns:
        return fallback
    try:
        s = df[col].dropna()
        if s.empty:
            return fallback
        if agg == "mean":
            return round(s.mean(), 2)
        elif agg == "max":
            return round(s.max(), 2)
        elif agg == "min":
            return round(s.min(), 2)
        elif agg == "idxmax":
            group_col = "building_id" if "building_id" in df.columns else "ap_id"
            if group_col in df.columns:
                return df.groupby(group_col)[col].mean().idxmax()
        return fallback
    except Exception:
        return fallback


def analyze_electricity(api_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No electricity data available."

    avg_cooling = _safe(df, "ac_cooling_energy")
    avg_sockets = _safe(df, "lights_and_sockets_energy")
    peak_total = _safe(df, "total_energy_usage", "max")
    avg_temp = _safe(df, "temperature")

    top_building = "N/A"
    if "building_id" in df.columns and "total_energy_usage" in df.columns:
        try:
            top_building = df.groupby("building_id")["total_energy_usage"].mean().idxmax()
        except Exception:
            pass

    prompt = (
        f"You are a Smart Campus Energy Efficiency Advisor for IIT Roorkee. Based on this energy data:\n"
        f"- Avg AC Cooling Load: {avg_cooling} kWh | Avg Lights & Sockets Load: {avg_sockets} kWh\n"
        f"- Peak Total Power Usage: {peak_total} kWh\n"
        f"- Avg Outdoor Temperature: {avg_temp}°C\n"
        f"- Highest consuming building: {top_building}\n\n"
        f"Give 3 precise, actionable energy saving recommendations.\n"
        f"For each recommendation, STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        f"### 1. [Main Topic Heading]\n"
        f"- ** Observation**: [What the data says in one bullet]\n"
        f"- ** Action**: [What to do immediately in one bullet]\n"
        f"- ** Impact**: [Expected savings or outcome in one bullet]\n\n"
        f"Keep the language simple — no technical jargon. Focus on AC scheduling, peak hour control, and building-level savings."
    )
    return _call_groq(api_key, prompt)


def analyze_wifi(api_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No WiFi data available."

    avg_devices = _safe(df, "connected_devices")
    peak_devices = _safe(df, "connected_devices", "max")
    avg_delay = _safe(df, "network_delay")
    avg_drops = _safe(df, "connection_drops")

    worst_ap = "N/A"
    if "ap_id" in df.columns and "network_delay" in df.columns:
        try:
            worst_ap = df.groupby("ap_id")["network_delay"].mean().idxmax()
        except Exception:
            pass

    prompt = (
        f"You are a Campus Network Optimization Specialist for IIT Roorkee. WiFi summary:\n"
        f"- Avg Connected Devices: {avg_devices} | Peak: {peak_devices}\n"
        f"- Avg Network Delay: {avg_delay} ms\n"
        f"- Worst performing access point: {worst_ap}\n"
        f"- Avg Signal Drops: {avg_drops}%\n\n"
        f"Give 3 specific network health recommendations.\n"
        f"For each recommendation, STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        f"### 1. [Main Topic Heading]\n"
        f"- ** Observation**: [What the data reveals in one bullet]\n"
        f"- ** Action**: [Concrete improvement in one bullet]\n"
        f"- ** Impact**: [Expected result in one bullet]\n\n"
        f"Explain in simple, non-technical language. Focus on busy hours, slow zones, and signal quality."
    )
    return _call_groq(api_key, prompt)


def analyze_mess(api_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No mess data available."

    avg_wait = _safe(df, "estimated_wait_min")
    peak_entries = _safe(df, "entries", "max")
    avg_rating = _safe(df, "student_rating")

    worst_mess = "N/A"
    if "mess_id" in df.columns and "estimated_wait_min" in df.columns:
        try:
            worst_mess = df.groupby("mess_id")["estimated_wait_min"].mean().idxmax()
        except Exception:
            pass

    rain_wait = "N/A"
    if "rain" in df.columns and "estimated_wait_min" in df.columns:
        rain_df = df[df["rain"] > 5]["estimated_wait_min"].dropna()
        if not rain_df.empty:
            rain_wait = round(rain_df.mean(), 1)

    prompt = (
        f"You are a Campus Dining Operations Expert for IIT Roorkee. Mess hall summary:\n"
        f"- Avg Wait Time: {avg_wait} min | Peak Entries in 1 hour: {peak_entries}\n"
        f"- Busiest Mess: {worst_mess}\n"
        f"- Avg Student Rating: {avg_rating}/5.0\n"
        f"- Avg Wait During Rain: {rain_wait} min\n\n"
        f"Give 3 targeted dining management recommendations.\n"
        f"For each recommendation, STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        f"### 1. [Main Topic Heading]\n"
        f"- ** Observation**: [Data-backed insight in one bullet]\n"
        f"- ** Action**: [Operational fix in one bullet]\n"
        f"- ** Impact**: [Expected result in one bullet]\n\n"
        f"Keep language simple. Focus on reducing queues, improving food ratings, and rainy day planning."
    )
    return _call_groq(api_key, prompt)


def analyze_library(api_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No library data available."

    avg_total = _safe(df, "total_occupancy")
    peak_total = _safe(df, "total_occupancy", "max")

    exam_occ = "N/A"
    if "event_type" in df.columns and "total_occupancy" in df.columns:
        exam_df = df[df["event_type"] == "exam_week"]["total_occupancy"].dropna()
        if not exam_df.empty:
            exam_occ = round(exam_df.mean(), 0)

    prompt = (
        f"You are a Campus Library Resource Planner for IIT Roorkee. Library occupancy summary:\n"
        f"- Avg Daily Occupancy: {avg_total} students\n"
        f"- Peak Total Occupancy: {peak_total} students\n"
        f"- Avg Occupancy During Exam Week: {exam_occ} students\n\n"
        f"Give 3 library management recommendations.\n"
        f"For each recommendation, STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        f"### 1. [Main Topic Heading]\n"
        f"- ** Observation**: [What occupancy patterns reveal in one bullet]\n"
        f"- ** Action**: [Practical improvement in one bullet]\n"
        f"- ** Impact**: [Expected result in one bullet]\n\n"
        f"Keep language simple. Focus on seating capacity, exam week planning, and study zone efficiency."
    )
    return _call_groq(api_key, prompt)


def analyze_transport(api_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No transport data available."

    avg_delay = _safe(df, "delay_minutes")
    peak_passengers = _safe(df, "passenger_count", "max")

    worst_route = "N/A"
    if "route" in df.columns and "delay_minutes" in df.columns:
        try:
            worst_route = df.groupby("route")["delay_minutes"].mean().idxmax()
        except Exception:
            pass

    rain_delay = "N/A"
    if "rain" in df.columns and "delay_minutes" in df.columns:
        rain_df = df[df["rain"] > 5]["delay_minutes"].dropna()
        if not rain_df.empty:
            rain_delay = round(rain_df.mean(), 1)

    prompt = (
        f"You are a Campus Transportation Logistics Expert for IIT Roorkee. Shuttle data:\n"
        f"- Avg Route Delay: {avg_delay} min | Peak Passengers: {peak_passengers}\n"
        f"- Most Delayed Route: {worst_route}\n"
        f"- Avg Delay During Rain: {rain_delay} min\n\n"
        f"Give 3 transport optimization recommendations.\n"
        f"For each recommendation, STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        f"### 1. [Main Topic Heading]\n"
        f"- ** Observation**: [Data insight in one bullet]\n"
        f"- ** Action**: [Concrete fix in one bullet]\n"
        f"- ** Impact**: [Expected result in one bullet]\n\n"
        f"Keep language simple. Focus on scheduling, rain contingency, and route load balancing."
    )
    return _call_groq(api_key, prompt)


def analyze_attendance(api_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No attendance data available."

    avg_present = _safe(df, "present")
    total_sessions = _safe(df, "ts", "nunique")

    prompt = (
        f"You are an Academic Success Strategist for IIT Roorkee. Attendance data:\n"
        f"- Avg Attendance Rate: {avg_present*100:.1f}%\n"
        f"- Total Class Sessions Analyzed: {total_sessions}\n\n"
        f"Give 3 student engagement recommendations.\n"
        f"For each recommendation, STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        f"### 1. [Main Topic Heading]\n"
        f"- ** Observation**: [Data insight in one bullet]\n"
        f"- ** Action**: [Practical intervention in one bullet]\n"
        f"- ** Impact**: [Expected result in one bullet]\n\n"
        f"Keep language simple. Focus on student retention, early warning signs, and schedule optimization."
    )
    return _call_groq(api_key, prompt)



def generate_groq_insights(api_key: str, context_df_dict: dict[str, pd.DataFrame]) -> str:
    campus_state = []

    if "electricity" in context_df_dict and not context_df_dict["electricity"].empty:
        e_df = context_df_dict["electricity"]
        campus_state.append(f"Electricity: Avg AC Cooling {_safe(e_df, 'ac_cooling_energy')} kWh, Avg Sockets {_safe(e_df, 'lights_and_sockets_energy')} kWh, Peak {_safe(e_df, 'total_energy_usage', 'max')} kWh")

    if "wifi" in context_df_dict and not context_df_dict["wifi"].empty:
        w_df = context_df_dict["wifi"]
        campus_state.append(f"WiFi: Avg {_safe(w_df, 'connected_devices')} devices, Peak delay {_safe(w_df, 'network_delay', 'max')} ms, Signal drops {_safe(w_df, 'connection_drops')}%")

    if "mess" in context_df_dict and not context_df_dict["mess"].empty:
        m_df = context_df_dict["mess"]
        campus_state.append(f"Mess: Avg wait {_safe(m_df, 'estimated_wait_min')} min, Rating {_safe(m_df, 'student_rating')}/5.0")

    if "library" in context_df_dict and not context_df_dict["library"].empty:
        l_df = context_df_dict["library"]
        campus_state.append(f"Library: Avg total occupancy {_safe(l_df, 'total_occupancy')}, Peak {_safe(l_df, 'total_occupancy', 'max')}")

    if "transport" in context_df_dict and not context_df_dict["transport"].empty:
        t_df = context_df_dict["transport"]
        campus_state.append(f"Transport: Avg delay {_safe(t_df, 'delay_minutes')} min, Peak passengers {_safe(t_df, 'passenger_count', 'max')}")

    if "attendance" in context_df_dict and not context_df_dict["attendance"].empty:
        a_df = context_df_dict["attendance"]
        campus_state.append(f"Attendance: Overall rate {_safe(a_df, 'present')*100:.1f}%")

    prompt = (
        "You are a Senior Smart Campus Intelligence AI for IIT Roorkee. Synthesize the following multi-domain campus telemetry:\n\n"
        + "\n".join(f"• {s}" for s in campus_state)
        + "\n\nProvide 4 cross-domain strategic recommendations that connect observations across departments (e.g., how mess wait times during exam week connect to shuttle demand and library congestion).\n"
        "STRICTLY use this exact bullet-point format (do NOT write paragraphs):\n"
        "### 1. [Main Strategic Heading]\n"
        "- ** Cross-System Observation**: [Multi-dataset insight in one bullet]\n"
        "- ** Strategic Action**: [High-impact recommendation in one bullet]\n"
        "- ** Expected Savings/Impact**: [Quantified benefit in one bullet]\n"
    )
    return _call_groq(api_key, prompt)
