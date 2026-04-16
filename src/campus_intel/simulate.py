from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import clamp, ensure_dir, write_json

@dataclass(frozen=True)
class SimConfig:
    seed: int = 42
    days: int = 60 # Ensuring March is fully covered when run in mid-April 2026
    freq_minutes: int = 60
    n_students: int = 1200
    n_courses: int = 16
    missing_rate: float = 0.005 # lower missing rate
    duplicate_rate: float = 0.001
    anomaly_rate: float = 0.002

def _ts_range(days: int, freq_minutes: int) -> pd.DatetimeIndex:
    end = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    return pd.date_range(start=start, end=end, freq=f"{freq_minutes}min", inclusive="left")

def _is_weekend(ts: pd.Series) -> pd.Series:
    return ts.dt.dayofweek >= 5

def _hour(ts: pd.Series) -> pd.Series:
    return ts.dt.hour.astype(int)

def _base_curve(hour: int, peaks: list[tuple[int, float]], base: float) -> float:
    val = base
    for mu, amp in peaks:
        val += amp * math.exp(-0.5 * ((hour - mu) / 2.2) ** 2)
    return val

def _get_event_type(d: datetime.date) -> str:
    # First week of March (March 1 to March 7, 2026) -> Exams
    if d.month == 3 and 1 <= d.day <= 7:
        return "exam_week"
    # Tech fest March 14-16
    if d.month == 3 and 14 <= d.day <= 16:
        return "cultural_fest"
    return "normal"

def generate_weather_context(ts_df: pd.DataFrame) -> pd.DataFrame:
    df = ts_df.copy()
    temps = []
    humidities = []
    rains = []
    event_types = []
    
    for i, row in df.iterrows():
        hour = row.ts.hour
        day_of_year = row.ts.dayofyear
        
        base_temp = 25.0 + 5.0 * math.sin((hour - 8) * math.pi / 12) 
        seasonal = 10.0 * math.sin(day_of_year * 2 * math.pi / 365)
        temp = base_temp + seasonal + np.random.normal(0, 1.5)
        
        humidity = clamp(60.0 - 1.5 * (temp - 20) + np.random.normal(0, 5), 20.0, 100.0)
        
        is_raining = random.random() < 0.03
        rain = clamp(np.random.exponential(5.0), 0.1, 50.0) if is_raining else 0.0
        if rain > 0:
            temp -= rain * 0.2
            humidity = clamp(humidity + 20, 0, 100)
            
        temps.append(temp)
        humidities.append(humidity)
        rains.append(rain)
        event_types.append(_get_event_type(row.ts.date()))
        
    df["temperature"] = np.round(temps, 1)
    df["humidity"] = np.round(humidities, 1)
    df["rain"] = np.round(rains, 1)
    df["event_type"] = event_types
    return df

def simulate_all(raw_dir: Path, processed_dir: Path, cfg: SimConfig = SimConfig()) -> dict[str, Path]:
    ensure_dir(raw_dir)
    ensure_dir(processed_dir)

    random.seed(cfg.seed)
    np.random.seed(cfg.seed)

    ts = _ts_range(cfg.days, cfg.freq_minutes)
    ts_df = pd.DataFrame({"ts": ts})
    weather_df = generate_weather_context(ts_df)

    # IIT Roorkee Topological Mapping
    buildings = pd.DataFrame([
        {"building_id": "B01", "building_name": "LHC", "building_type": "academic"},
        {"building_id": "B02", "building_name": "MAC_Building", "building_type": "academic"},
        {"building_id": "B03", "building_name": "Computer_Science_Dept", "building_type": "academic"},
        {"building_id": "B04", "building_name": "Mahendra_Bhawan_Library", "building_type": "library"},
        {"building_id": "B05", "building_name": "Rajendra_Bhawan", "building_type": "residential"},
        {"building_id": "B06", "building_name": "Sarojini_Bhawan", "building_type": "residential"},
        {"building_id": "B07", "building_name": "Ganga_Bhawan", "building_type": "residential"},
        {"building_id": "B08", "building_name": "Mechanical_Dept", "building_type": "academic"}
    ])

    messes = pd.DataFrame([
        {"mess_id": "M01", "mess_name": "Rajendra_Mess", "capacity": 350},
        {"mess_id": "M02", "mess_name": "Sarojini_Mess", "capacity": 280},
        {"mess_id": "M03", "mess_name": "Ganga_Mess", "capacity": 400}
    ])
    
    libraries = buildings[buildings["building_type"] == "library"]
    
    buses = pd.DataFrame([
        {"bus_id": "Bus_01", "route": "Main_Gate_to_LHC", "capacity": 40},
        {"bus_id": "Bus_02", "route": "Hostel_Area_to_MAC", "capacity": 40},
        {"bus_id": "Bus_03", "route": "Hostel_Area_to_Library", "capacity": 40}
    ])

    aps_rows: list[dict] = []
    for _, b in buildings.iterrows():
        aps_rows.append({"ap_id": f"AP_{b.building_id}_01", "building_id": b.building_id, "ap_name": f"{b.building_name}_AP_Primary"})
        if b.building_type == "academic" or b.building_type == "library":
             aps_rows.append({"ap_id": f"AP_{b.building_id}_02", "building_id": b.building_id, "ap_name": f"{b.building_name}_AP_Secondary"})
    wifi_aps = pd.DataFrame(aps_rows)

    # 1. Electricity
    elec_rows: list[pd.DataFrame] = []
    for _, b in buildings.iterrows():
        df = weather_df.copy()
        df["building_id"] = b.building_id

        h = _hour(df.ts)
        weekend = _is_weekend(df.ts)

        if b.building_type == "academic":
            base = 150.0
            peaks = [(10, 180.0), (15, 200.0)]
            weekend_scale = 0.3
        elif b.building_type == "residential":
            base = 80.0
            peaks = [(8, 60.0), (21, 140.0)]
            weekend_scale = 1.1
        else: # library
            base = 60.0
            peaks = [(15, 80.0), (20, 120.0)]
            weekend_scale = 1.0

        plug_load = []
        hvac_load = []
        for i in range(len(df)):
            hour = int(h.iat[i])
            is_wknd = bool(weekend.iat[i])
            evt = df.at[i, "event_type"]
            val = _base_curve(hour, peaks=peaks, base=base)
            val *= weekend_scale if is_wknd else 1.0
            
            # Library open 24/7 one week before exams (Feb 22 to Feb 28)
            d = df.at[i, "ts"].date()
            exam_prep = (d.month == 2 and 22 <= d.day <= 28)
            
            if b.building_type == "library":
                if evt == "exam_week" or exam_prep:
                    val *= 1.4 # High activity
                elif 0 <= hour <= 5: 
                    val = 20.0 # Closed base power

            plug_v = clamp(val + np.random.normal(0, 10.0), 10.0, 500.0)
            
            # AC depends on temp
            temp = df.at[i, "temperature"]
            hvac_v = 0.0
            if temp > 24:
                hvac_v = clamp(((temp - 24)**2) * 2.0 + np.random.normal(0, 5.0), 0.0, 300.0)
                if b.building_type == "library" and (0 <= hour <= 5) and not (evt == "exam_week" or exam_prep):
                    hvac_v = 0.0 # AC off when closed
            
            plug_load.append(plug_v)
            hvac_load.append(hvac_v)

        df["lights_and_sockets_energy"] = np.round(plug_load, 1)
        df["ac_cooling_energy"] = np.round(hvac_load, 1)
        df["total_energy_usage"] = df["lights_and_sockets_energy"] + df["ac_cooling_energy"]
        df["peak_power_drain"] = np.round((df["total_energy_usage"] * 1.2), 1)
        elec_rows.append(df)

    electricity = pd.concat(elec_rows, ignore_index=True)

    # 2. WiFi User QoS and Context
    wifi_rows: list[pd.DataFrame] = []
    for _, ap in wifi_aps.iterrows():
        btype = buildings.loc[buildings.building_id == ap.building_id, "building_type"].iat[0]
        df = weather_df.copy()
        df["ap_id"] = ap.ap_id

        h = _hour(df.ts)
        weekend = _is_weekend(df.ts)

        connected = []
        throughput = []
        packet_loss = []
        latency = []
        for i in range(len(df)):
            hour = int(h.iat[i])
            is_wknd = bool(weekend.iat[i])
            evt = df.at[i, "event_type"]
            d = df.at[i, "ts"].date()
            exam_prep = (d.month == 2 and 22 <= d.day <= 28)
            
            # Devices Model
            if btype == "academic":
                val = _base_curve(hour, [(10, 80), (14, 90)], 5.0) * (0.2 if is_wknd else 1.0)
            elif btype == "residential":
                val = _base_curve(hour, [(8, 40), (22, 100)], 20.0)
            else: # Library
                val = _base_curve(hour, [(16, 80), (20, 110)], 10.0)
                if evt == "exam_week" or exam_prep: val *= 1.5
                if (0 <= hour <= 5) and not (evt == "exam_week" or exam_prep): val = 0.0 # Closed
                
            if evt == "cultural_fest" and btype == "academic": val *= 0.3 # nobody in class
                
            c = int(clamp(val + np.random.normal(0, 5), 0, 150))
            
            th_mb = clamp(c * 1.5 + np.random.rand()*5, 0.0, 500.0)
            ploss = clamp((c / 150.0)**2 * 2.0, 0.0, 3.0) # max 3% loss
            lat = clamp(18.0 + (c / 150.0) * 45.0 + np.random.normal(0, 2), 15.0, 100.0)
            
            connected.append(c)
            throughput.append(th_mb)
            packet_loss.append(ploss)
            latency.append(lat)

        df["connected_devices"] = connected
        df["internet_speed"] = np.round(throughput, 1)
        df["connection_drops"] = np.round(packet_loss, 2)
        df["network_delay"] = np.round(latency, 1)
        wifi_rows.append(df)

    wifi = pd.concat(wifi_rows, ignore_index=True)

    # 3. Mess Footfall (with contextual feedback & menus)
    mess_rows: list[pd.DataFrame] = []
    
    for _, m in messes.iterrows():
        df = weather_df.copy()
        df["mess_id"] = m.mess_id
        h = _hour(df.ts)

        entries = []
        wait = []
        ratings = []
        meal_types = []
        served_menu = []
        
        for i in range(len(df)):
            hour = int(h.iat[i])
            rain = float(df.at[i, "rain"])
            
            # Determine Meal Type
            mtype = "None"
            target_ents = 0
            if 7 <= hour <= 9: 
                mtype = "Breakfast"
                target_ents = random.randint(80, 250)
            elif 12 <= hour <= 14: 
                mtype = "Lunch"
                target_ents = random.randint(150, 350)
            elif 19 <= hour <= 21: 
                mtype = "Dinner"
                target_ents = random.randint(180, 420)
                
            ents = target_ents if mtype != "None" else 0
            
            # Weather disruption
            if rain > 10.0 and mtype != "None":
                ents = int(ents * 1.2 if "Rajendra" in m.mess_name else ents * 0.8) # Crowd goes to largest mess
                
            crowd_ratio = ents / float(m.capacity) if ents > 0 else 0
            wait_min = clamp((crowd_ratio**2) * 20.0 + np.random.normal(0, 1.0), 0.0, 45.0) if ents > 0 else 0.0
            
            menu = "Closed"
            if mtype != "None":
                 menu = random.choice(["North Indian", "South Indian", "Nutrition Diet"]) if df.at[i, 'event_type'] != 'cultural_fest' else "Fest Special"
            
            rating = max(1.0, 5.0 - (wait_min / 15.0) + np.random.normal(0, 0.3)) if mtype != "None" else np.nan
            
            entries.append(ents)
            wait.append(wait_min)
            meal_types.append(mtype)
            served_menu.append(menu)
            ratings.append(rating)

        df["entries"] = entries
        df["estimated_wait_min"] = np.round(wait, 1)
        df["meal_type"] = meal_types
        df["menu_served"] = served_menu
        df["student_rating"] = np.round(ratings, 1)
        mess_rows.append(df)

    mess_footfall = pd.concat(mess_rows, ignore_index=True)

    # 4. Attendance
    students = [f"S{idx:05d}" for idx in range(1, cfg.n_students + 1)]
    courses = [f"C{idx:03d}" for idx in range(1, cfg.n_courses + 1)]
    class_hours = {9, 10, 11, 12, 14, 15, 16}
    att_base = weather_df.copy()
    att_base = att_base[att_base.ts.dt.hour.isin(class_hours)]
    att_base = att_base[~_is_weekend(att_base.ts)]
    att_base = att_base.sample(frac=0.45, random_state=cfg.seed).sort_values("ts").reset_index(drop=True)

    att_rows = []
    for _, row in att_base.iterrows():
        course = random.choice(courses)
        room = random.choice(list(buildings[buildings.building_type=="academic"].building_id))
        class_size = random.randint(40, 100)
        enrolled = random.sample(students, k=class_size)
        for sid in enrolled:
            weather_drop = 0.15 if float(row.rain) > 5.0 else 0.0
            event_drop = 0.8 if row.event_type in ["cultural_fest", "exam_week"] else 0.0
            p = clamp(0.85 - weather_drop - event_drop, 0.05, 1.0)
            att_rows.append({"ts": row.ts, "student_id": sid, "course_id": course, "room_id": room, "present": 1 if random.random() < p else 0, "weather_context": f"{row.temperature}C, {row.rain}mm rain"})

    attendance = pd.DataFrame(att_rows)

    # 5. Library Occupancy
    lib_rows: list[pd.DataFrame] = []
    for _, lib in libraries.iterrows():
        df = weather_df.copy()
        df["building_id"] = lib.building_id
        h = _hour(df.ts)
        
        occ_quiet = []
        occ_collab = []
        for i in range(len(df)):
            hr = int(h.iat[i])
            evt = df.at[i, "event_type"]
            d = df.at[i, "ts"].date()
            exam_prep = (d.month == 2 and 22 <= d.day <= 28)
            
            is_closed = (0 <= hr <= 5) and not (evt == "exam_week" or exam_prep)
            
            if is_closed:
                oq, oc = 0, 0
            else:
                base_q = _base_curve(hr, [(15, 60), (20, 100)], 20.0)
                base_c = _base_curve(hr, [(14, 50), (19, 80)], 10.0)
                
                if evt == "exam_week" or exam_prep:
                    base_q *= 2.0
                    base_c *= 1.5
                    
                oq = int(clamp(base_q + np.random.normal(0, 5), 0, 200))
                oc = int(clamp(base_c + np.random.normal(0, 5), 0, 200))
                
            occ_quiet.append(oq)
            occ_collab.append(oc)
            
        df["occupancy_quiet_zone"] = occ_quiet
        df["occupancy_collab_zone"] = occ_collab
        df["total_occupancy"] = np.array(occ_quiet) + np.array(occ_collab)
        lib_rows.append(df)
            
    library_occupancy = pd.concat(lib_rows, ignore_index=True) if lib_rows else pd.DataFrame()

    # 6. Shuttle Transport
    trans_rows: list[pd.DataFrame] = []
    for _, bus in buses.iterrows():
        df = weather_df.copy()
        df["bus_id"] = bus.bus_id
        df["route"] = bus.route
        h = _hour(df.ts)
        
        passengers = []
        delay = []
        for i in range(len(df)):
            hr = int(h.iat[i])
            if 0 <= hr <= 6:
                p, d = 0, 0.0
            else:
                base_p = _base_curve(hr, [(9, 60), (17, 65)], 10.0)
                if float(df.at[i, "rain"]) > 0:
                    base_p *= 1.3
                
                p = int(clamp(base_p + np.random.normal(0, 5), 0, 70))
                
                d = clamp((p / 40.0) * 4.0 + (float(df.at[i, "rain"]) * 0.5) + np.random.normal(0, 1), 0.0, 15.0)
                
            passengers.append(p)
            delay.append(d)
                
        df["passenger_count"] = passengers
        df["delay_minutes"] = np.round(delay, 1)
        trans_rows.append(df)
        
    shuttle_transport = pd.concat(trans_rows, ignore_index=True)

    # Inject missingness / duplicates
    def inject_issues(df2: pd.DataFrame) -> pd.DataFrame:
        if df2.empty: return df2
        df2 = df2.copy()
        n = len(df2)
        drop_n = int(n * cfg.missing_rate)
        if drop_n > 0:
            df2 = df2.drop(index=np.random.choice(df2.index.values, size=drop_n, replace=False))
        dup_n = int(n * cfg.duplicate_rate)
        if dup_n > 0:
            dup_idx = np.random.choice(df2.index.values, size=dup_n, replace=False)
            df2 = pd.concat([df2, df2.loc[dup_idx]], ignore_index=True)
        return df2.sort_values("ts").reset_index(drop=True)

    # Write CSVs
    out = {}
    buildings.to_csv(raw_dir / "buildings.csv", index=False)
    messes.to_csv(raw_dir / "messes.csv", index=False)
    buses.to_csv(raw_dir / "buses.csv", index=False)
    wifi_aps.to_csv(raw_dir / "wifi_aps.csv", index=False)
    
    inject_issues(electricity).to_csv(raw_dir / "electricity_usage_raw.csv", index=False)
    inject_issues(wifi).to_csv(raw_dir / "wifi_usage_raw.csv", index=False)
    inject_issues(mess_footfall).to_csv(raw_dir / "mess_footfall_raw.csv", index=False)
    attendance.to_csv(raw_dir / "attendance_logs_raw.csv", index=False)
    if not library_occupancy.empty:
        inject_issues(library_occupancy).to_csv(raw_dir / "library_occupancy_raw.csv", index=False)
    inject_issues(shuttle_transport).to_csv(raw_dir / "shuttle_transport_raw.csv", index=False)

    out.update({
        "buildings": raw_dir / "buildings.csv",
        "messes": raw_dir / "messes.csv",
        "buses": raw_dir / "buses.csv",
        "wifi_aps": raw_dir / "wifi_aps.csv",
        "electricity_usage_raw": raw_dir / "electricity_usage_raw.csv",
        "wifi_usage_raw": raw_dir / "wifi_usage_raw.csv",
        "mess_footfall_raw": raw_dir / "mess_footfall_raw.csv",
        "attendance_logs_raw": raw_dir / "attendance_logs_raw.csv",
        "library_occupancy_raw": raw_dir / "library_occupancy_raw.csv",
        "shuttle_transport_raw": raw_dir / "shuttle_transport_raw.csv",
    })

    labels_path = processed_dir / "injected_anomaly_labels.json"
    write_json(labels_path, {"labels": []})
    out["injected_anomaly_labels"] = labels_path

    return out
