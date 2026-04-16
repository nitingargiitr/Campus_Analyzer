from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import get_paths
from .db import connect_sqlite, exec_sql_file
from .etl import run_etl
from .models.anomaly import detect_anomalies, score_against_injected
from .models.forecast import run_electricity_forecast
from .models.mess_peak import run_peak_mess_prediction
from .recommend import build_recommendations
from .simulate import SimConfig, simulate_all
from .utils import ensure_dir, write_json


def run_all(root: Path | None = None, sim_cfg: SimConfig = SimConfig()) -> dict:
    paths = get_paths(root)
    ensure_dir(paths.data_dir)
    ensure_dir(paths.raw_dir)
    ensure_dir(paths.processed_dir)

    # 1) Simulate raw datasets
    sim_out = simulate_all(paths.raw_dir, paths.processed_dir, sim_cfg)

    # 2) ETL into SQLite + exports
    etl_out = run_etl(
        raw_dir=paths.raw_dir,
        processed_dir=paths.processed_dir,
        db_path=paths.db_path,
        sql_dir=paths.root / "src" / "campus_intel" / "sql",
    )

    # Load processed dataframes for ML steps
    electricity = pd.read_csv(paths.processed_dir / "electricity_usage.csv")
    wifi = pd.read_csv(paths.processed_dir / "wifi_usage.csv")
    mess = pd.read_csv(paths.processed_dir / "mess_footfall.csv")

    # 3) ML: forecasting
    daily_forecast, fc_metrics = run_electricity_forecast(electricity)

    # 4) ML: anomaly detection
    labels = json.loads((paths.processed_dir / "injected_anomaly_labels.json").read_text(encoding="utf-8")).get("labels", [])
    anoms_e = detect_anomalies(electricity, entity_type="building", entity_col="building_id", metric="total_energy_usage", z_threshold=3.2)
    anoms_w = detect_anomalies(wifi, entity_type="ap", entity_col="ap_id", metric="connected_devices", z_threshold=3.2)
    anoms_m = detect_anomalies(mess, entity_type="mess", entity_col="mess_id", metric="entries", z_threshold=3.2)
    anomalies = pd.concat([anoms_e, anoms_w, anoms_m], ignore_index=True)
    anom_metrics = score_against_injected(anomalies, labels)

    # 5) ML: peak mess hour prediction
    peak_mess_forecast, peak_metrics = run_peak_mess_prediction(mess)

    # 6) Recommendations
    recs = build_recommendations(
        electricity_usage=electricity,
        wifi_usage=wifi,
        mess_footfall=mess,
        anomalies=anomalies[anomalies["is_anomaly"] == 1].copy(),
        forecast_elec_daily=daily_forecast,
        peak_mess_forecast=peak_mess_forecast,
    )

    # 7) Write ML outputs to SQL + exports for Tableau
    conn = connect_sqlite(paths.db_path)
    # ensure schema/views exist (ETL already did, but safe)
    exec_sql_file(conn, paths.root / "src" / "campus_intel" / "sql" / "schema.sql")
    exec_sql_file(conn, paths.root / "src" / "campus_intel" / "sql" / "views.sql")

    anomalies.to_sql("anomalies", conn, if_exists="replace", index=False)
    daily_forecast.to_sql("forecast_electricity_daily", conn, if_exists="replace", index=False)
    peak_mess_forecast.to_sql("peak_mess_hours_forecast", conn, if_exists="replace", index=False)
    recs.to_sql("recommendations", conn, if_exists="replace", index=False)

    exec_sql_file(conn, paths.root / "src" / "campus_intel" / "sql" / "views.sql")
    conn.close()

    # Exports
    anomalies.to_csv(paths.processed_dir / "anomalies.csv", index=False)
    daily_forecast.to_csv(paths.processed_dir / "forecast_electricity_daily.csv", index=False)
    peak_mess_forecast.to_csv(paths.processed_dir / "peak_mess_hours_forecast.csv", index=False)
    recs.to_csv(paths.processed_dir / "recommendations.csv", index=False)

    metrics_out = {
        "electricity_forecast": fc_metrics.__dict__,
        "anomaly_detection": anom_metrics.__dict__,
        "peak_mess_prediction": peak_metrics.__dict__,
    }
    write_json(paths.processed_dir / "model_metrics.json", metrics_out)

    return {
        "db_path": str(paths.db_path),
        "processed_dir": str(paths.processed_dir),
        "metrics": metrics_out,
    }

