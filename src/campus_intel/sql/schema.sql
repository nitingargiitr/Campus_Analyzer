-- Core fact tables

CREATE TABLE IF NOT EXISTS buildings (
  building_id TEXT PRIMARY KEY,
  building_name TEXT NOT NULL,
  building_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messes (
  mess_id TEXT PRIMARY KEY,
  mess_name TEXT NOT NULL,
  capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS wifi_aps (
  ap_id TEXT PRIMARY KEY,
  building_id TEXT NOT NULL,
  ap_name TEXT NOT NULL,
  FOREIGN KEY(building_id) REFERENCES buildings(building_id)
);

CREATE TABLE IF NOT EXISTS buses (
  bus_id TEXT PRIMARY KEY,
  route TEXT NOT NULL,
  capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance_logs (
  ts TEXT NOT NULL,
  student_id TEXT NOT NULL,
  course_id TEXT NOT NULL,
  room_id TEXT NOT NULL,
  present INTEGER NOT NULL,
  weather_context TEXT,
  PRIMARY KEY (ts, student_id, course_id)
);

CREATE TABLE IF NOT EXISTS wifi_usage (
  ts TEXT NOT NULL,
  ap_id TEXT NOT NULL,
  temperature_c REAL NOT NULL,
  humidity REAL NOT NULL,
  rain_mm REAL NOT NULL,
  event_type TEXT NOT NULL,
  connected_devices INTEGER NOT NULL,
  throughput_mbps REAL NOT NULL,
  packet_loss_pct REAL NOT NULL,
  latency_ms REAL NOT NULL,
  is_imputed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, ap_id),
  FOREIGN KEY(ap_id) REFERENCES wifi_aps(ap_id)
);

CREATE TABLE IF NOT EXISTS electricity_usage (
  ts TEXT NOT NULL,
  building_id TEXT NOT NULL,
  temperature_c REAL NOT NULL,
  humidity REAL NOT NULL,
  rain_mm REAL NOT NULL,
  event_type TEXT NOT NULL,
  plug_load_kwh REAL NOT NULL,
  hvac_load_kwh REAL NOT NULL,
  total_kwh REAL NOT NULL,
  peak_kw REAL NOT NULL,
  is_imputed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, building_id),
  FOREIGN KEY(building_id) REFERENCES buildings(building_id)
);

CREATE TABLE IF NOT EXISTS mess_footfall (
  ts TEXT NOT NULL,
  mess_id TEXT NOT NULL,
  temperature_c REAL NOT NULL,
  humidity REAL NOT NULL,
  rain_mm REAL NOT NULL,
  event_type TEXT NOT NULL,
  entries INTEGER NOT NULL,
  estimated_wait_min REAL NOT NULL,
  meal_type TEXT,
  menu_served TEXT,
  student_rating REAL,
  is_imputed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, mess_id),
  FOREIGN KEY(mess_id) REFERENCES messes(mess_id)
);

CREATE TABLE IF NOT EXISTS library_occupancy (
  ts TEXT NOT NULL,
  building_id TEXT NOT NULL,
  temperature_c REAL NOT NULL,
  humidity REAL NOT NULL,
  rain_mm REAL NOT NULL,
  event_type TEXT NOT NULL,
  occupancy_quiet_zone INTEGER NOT NULL,
  occupancy_collab_zone INTEGER NOT NULL,
  total_occupancy INTEGER NOT NULL,
  is_imputed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, building_id),
  FOREIGN KEY(building_id) REFERENCES buildings(building_id)
);

CREATE TABLE IF NOT EXISTS shuttle_transport (
  ts TEXT NOT NULL,
  bus_id TEXT NOT NULL,
  route TEXT NOT NULL,
  temperature_c REAL NOT NULL,
  humidity REAL NOT NULL,
  rain_mm REAL NOT NULL,
  event_type TEXT NOT NULL,
  passenger_count INTEGER NOT NULL,
  delay_minutes REAL NOT NULL,
  is_imputed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (ts, bus_id),
  FOREIGN KEY(bus_id) REFERENCES buses(bus_id)
);

-- ML outputs

CREATE TABLE IF NOT EXISTS anomalies (
  ts TEXT NOT NULL,
  entity_type TEXT NOT NULL,         -- 'building' | 'ap' | 'mess'
  entity_id TEXT NOT NULL,
  metric TEXT NOT NULL,              -- 'total_kwh' | 'connected_devices' | ...
  value REAL NOT NULL,
  score REAL NOT NULL,
  is_anomaly INTEGER NOT NULL,
  reason TEXT NOT NULL,
  PRIMARY KEY (ts, entity_type, entity_id, metric)
);

CREATE TABLE IF NOT EXISTS forecast_electricity_daily (
  day TEXT NOT NULL,
  building_id TEXT NOT NULL,
  kwh_forecast REAL NOT NULL,
  kwh_actual REAL,
  model_name TEXT NOT NULL,
  PRIMARY KEY (day, building_id, model_name)
);

CREATE TABLE IF NOT EXISTS peak_mess_hours_forecast (
  ts TEXT NOT NULL,                  -- forecast timestamp (next hour)
  mess_id TEXT NOT NULL,
  peak_prob REAL NOT NULL,
  predicted_peak INTEGER NOT NULL,
  entries_forecast REAL NOT NULL,
  model_name TEXT NOT NULL,
  PRIMARY KEY (ts, mess_id, model_name)
);

CREATE TABLE IF NOT EXISTS recommendations (
  rec_id TEXT PRIMARY KEY,
  created_ts TEXT NOT NULL,
  category TEXT NOT NULL,            -- 'energy' | 'wifi' | 'mess' | 'schedule' | 'resource'
  target_type TEXT NOT NULL,         -- 'building' | 'ap' | 'mess' | 'campus'
  target_id TEXT NOT NULL,
  time_window TEXT NOT NULL,         -- human-readable window
  reason TEXT NOT NULL,
  confidence REAL NOT NULL,
  expected_impact TEXT NOT NULL,
  priority INTEGER NOT NULL
);
