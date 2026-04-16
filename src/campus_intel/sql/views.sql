-- KPI views for Tableau

DROP VIEW IF EXISTS v_kpi_overview_daily;
CREATE VIEW v_kpi_overview_daily AS
WITH daily_energy AS (
  SELECT date(ts) AS day, SUM(total_kwh) AS total_kwh
  FROM electricity_usage
  GROUP BY date(ts)
),
daily_wifi AS (
  SELECT date(ts) AS day, AVG(connected_devices) AS avg_connected_devices
  FROM wifi_usage
  GROUP BY date(ts)
),
daily_mess AS (
  SELECT date(ts) AS day, SUM(entries) AS total_mess_entries, AVG(estimated_wait_min) AS avg_wait_min
  FROM mess_footfall
  GROUP BY date(ts)
)
SELECT
  e.day AS day,
  e.total_kwh AS total_kwh,
  w.avg_connected_devices AS avg_connected_devices,
  m.total_mess_entries AS total_mess_entries,
  m.avg_wait_min AS avg_wait_min
FROM daily_energy e
LEFT JOIN daily_wifi w ON w.day = e.day
LEFT JOIN daily_mess m ON m.day = e.day;

DROP VIEW IF EXISTS v_peak_usage_by_hour;
CREATE VIEW v_peak_usage_by_hour AS
SELECT
  strftime('%Y-%m-%d', ts) AS day,
  CAST(strftime('%H', ts) AS INTEGER) AS hour,
  SUM(total_kwh) AS total_kwh,
  AVG(connected_devices) AS avg_connected_devices,
  SUM(entries) AS total_mess_entries,
  AVG(estimated_wait_min) AS avg_wait_min
FROM electricity_usage eu
JOIN wifi_usage wu ON wu.ts = eu.ts
JOIN mess_footfall mf ON mf.ts = eu.ts
GROUP BY strftime('%Y-%m-%d', ts), CAST(strftime('%H', ts) AS INTEGER);

DROP VIEW IF EXISTS v_anomalies;
CREATE VIEW v_anomalies AS
SELECT
  ts,
  entity_type,
  entity_id,
  metric,
  value,
  score,
  is_anomaly,
  reason
FROM anomalies
WHERE is_anomaly = 1;

DROP VIEW IF EXISTS v_forecast_electricity_daily;
CREATE VIEW v_forecast_electricity_daily AS
SELECT
  day,
  building_id,
  kwh_forecast,
  kwh_actual,
  model_name
FROM forecast_electricity_daily;

DROP VIEW IF EXISTS v_peak_mess_hours_forecast;
CREATE VIEW v_peak_mess_hours_forecast AS
SELECT
  ts,
  mess_id,
  peak_prob,
  predicted_peak,
  entries_forecast,
  model_name
FROM peak_mess_hours_forecast;

DROP VIEW IF EXISTS v_recommendations;
CREATE VIEW v_recommendations AS
SELECT
  rec_id,
  created_ts,
  category,
  target_type,
  target_id,
  time_window,
  reason,
  confidence,
  expected_impact,
  priority
FROM recommendations
ORDER BY priority ASC, confidence DESC;
