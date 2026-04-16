from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .db import connect_sqlite, exec_sql_file
from .utils import ensure_dir, write_json


@dataclass(frozen=True)
class EtlReport:
    table: str
    rows_in: int
    rows_out: int
    duplicates_dropped: int
    missing_imputed: int
    invalid_ids_dropped: int


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


def _dedupe(df: pd.DataFrame, subset: list[str]) -> tuple[pd.DataFrame, int]:
    before = len(df)
    df2 = df.drop_duplicates(subset=subset, keep="last")
    return df2, before - len(df2)


def _drop_invalid_ids(df: pd.DataFrame, col: str, valid: set[str]) -> tuple[pd.DataFrame, int]:
    before = len(df)
    df2 = df[df[col].isin(valid)].copy()
    return df2, before - len(df2)


def run_etl(raw_dir: Path, processed_dir: Path, db_path: Path, sql_dir: Path) -> dict:
    ensure_dir(processed_dir)

    buildings = _read_csv(raw_dir / "buildings.csv")
    messes = _read_csv(raw_dir / "messes.csv")
    wifi_aps = _read_csv(raw_dir / "wifi_aps.csv")
    buses = _read_csv(raw_dir / "buses.csv")

    electricity = _read_csv(raw_dir / "electricity_usage_raw.csv")
    wifi = _read_csv(raw_dir / "wifi_usage_raw.csv")
    mess = _read_csv(raw_dir / "mess_footfall_raw.csv")
    attendance = _read_csv(raw_dir / "attendance_logs_raw.csv")
    library = _read_csv(raw_dir / "library_occupancy_raw.csv")
    transport = _read_csv(raw_dir / "shuttle_transport_raw.csv")

    valid_buildings = set(buildings["building_id"].astype(str)) if not buildings.empty else set()
    valid_messes = set(messes["mess_id"].astype(str)) if not messes.empty else set()
    valid_aps = set(wifi_aps["ap_id"].astype(str)) if not wifi_aps.empty else set()
    valid_buses = set(buses["bus_id"].astype(str)) if not buses.empty else set()

    reports: list[EtlReport] = []

    # Electricity
    e_in = len(electricity)
    electricity, dup = _dedupe(electricity, ["ts", "building_id"])
    electricity, bad = _drop_invalid_ids(electricity, "building_id", valid_buildings)
    electricity["is_imputed"] = 0
    reports.append(EtlReport("electricity_usage", e_in, len(electricity), dup, 0, bad))

    # WiFi
    w_in = len(wifi)
    wifi, dup = _dedupe(wifi, ["ts", "ap_id"])
    wifi, bad = _drop_invalid_ids(wifi, "ap_id", valid_aps)
    wifi["is_imputed"] = 0
    reports.append(EtlReport("wifi_usage", w_in, len(wifi), dup, 0, bad))

    # Mess
    m_in = len(mess)
    mess, dup = _dedupe(mess, ["ts", "mess_id"])
    mess, bad = _drop_invalid_ids(mess, "mess_id", valid_messes)
    mess["is_imputed"] = 0
    reports.append(EtlReport("mess_footfall", m_in, len(mess), dup, 0, bad))

    # Attendance
    a_in = len(attendance)
    attendance, dup = _dedupe(attendance, ["ts", "student_id", "course_id"])
    attendance = attendance.dropna(subset=["ts", "student_id", "course_id"]).copy()
    attendance["present"] = attendance["present"].astype(int).clip(0, 1)
    reports.append(EtlReport("attendance_logs", a_in, len(attendance), dup, 0, 0))
    
    # Library
    l_in = len(library)
    if not library.empty:
        library, dup = _dedupe(library, ["ts", "building_id"])
        library, bad = _drop_invalid_ids(library, "building_id", valid_buildings)
        library["is_imputed"] = 0
        reports.append(EtlReport("library_occupancy", l_in, len(library), dup, 0, bad))
        
    # Transport
    t_in = len(transport)
    if not transport.empty:
        transport, dup = _dedupe(transport, ["ts", "bus_id"])
        transport, bad = _drop_invalid_ids(transport, "bus_id", valid_buses)
        transport["is_imputed"] = 0
        reports.append(EtlReport("shuttle_transport", t_in, len(transport), dup, 0, bad))

    # Write processed exports
    if not buildings.empty: buildings.to_csv(processed_dir / "buildings.csv", index=False)
    if not messes.empty: messes.to_csv(processed_dir / "messes.csv", index=False)
    if not wifi_aps.empty: wifi_aps.to_csv(processed_dir / "wifi_aps.csv", index=False)
    if not buses.empty: buses.to_csv(processed_dir / "buses.csv", index=False)
    
    electricity.to_csv(processed_dir / "electricity_usage.csv", index=False)
    wifi.to_csv(processed_dir / "wifi_usage.csv", index=False)
    mess.to_csv(processed_dir / "mess_footfall.csv", index=False)
    attendance.to_csv(processed_dir / "attendance_logs.csv", index=False)
    if not library.empty: library.to_csv(processed_dir / "library_occupancy.csv", index=False)
    if not transport.empty: transport.to_csv(processed_dir / "shuttle_transport.csv", index=False)

    quality = {"reports": [r.__dict__ for r in reports], "generated_from": str(raw_dir)}
    write_json(processed_dir / "quality_report.json", quality)

    # Load into SQLite
    conn = connect_sqlite(db_path)
    exec_sql_file(conn, sql_dir / "schema.sql")

    if not buildings.empty: buildings.to_sql("buildings", conn, if_exists="replace", index=False)
    if not messes.empty: messes.to_sql("messes", conn, if_exists="replace", index=False)
    if not wifi_aps.empty: wifi_aps.to_sql("wifi_aps", conn, if_exists="replace", index=False)
    if not buses.empty: buses.to_sql("buses", conn, if_exists="replace", index=False)
    
    electricity.assign(ts=electricity["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("electricity_usage", conn, if_exists="replace", index=False)
    wifi.assign(ts=wifi["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("wifi_usage", conn, if_exists="replace", index=False)
    mess.assign(ts=mess["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("mess_footfall", conn, if_exists="replace", index=False)
    attendance.assign(ts=attendance["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("attendance_logs", conn, if_exists="replace", index=False)
    if not library.empty: library.assign(ts=library["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("library_occupancy", conn, if_exists="replace", index=False)
    if not transport.empty: transport.assign(ts=transport["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")).to_sql("shuttle_transport", conn, if_exists="replace", index=False)

    exec_sql_file(conn, sql_dir / "views.sql")
    conn.close()

    return {"quality_report": quality, "processed_dir": str(processed_dir), "db_path": str(db_path)}
