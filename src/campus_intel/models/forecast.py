from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error


@dataclass(frozen=True)
class ForecastResult:
    model_name: str
    mae: float
    mape: float


def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["day"] = df["ts"].dt.floor("D")
    df["hour"] = df["ts"].dt.hour
    df["dow"] = df["ts"].dt.dayofweek
    # lags per building
    df = df.sort_values(["building_id", "ts"])
    df["total_energy_usage_lag_1"] = df.groupby("building_id")["total_energy_usage"].shift(1)
    df["total_energy_usage_lag_24"] = df.groupby("building_id")["total_energy_usage"].shift(24)
    df["total_energy_usage_roll_24"] = df.groupby("building_id")["total_energy_usage"].shift(1).rolling(24).mean().reset_index(level=0, drop=True)
    df = df.dropna(subset=["total_energy_usage_lag_1", "total_energy_usage_lag_24", "total_energy_usage_roll_24"]).copy()
    return df


def run_electricity_forecast(electricity_usage: pd.DataFrame) -> tuple[pd.DataFrame, ForecastResult]:
    df = electricity_usage.copy()
    feats = _make_features(df)

    X = feats[["hour", "dow", "total_energy_usage_lag_1", "total_energy_usage_lag_24", "total_energy_usage_roll_24"]]
    y = feats["total_energy_usage"].values

    cutoff = feats["ts"].max() - pd.Timedelta(days=7)
    train_mask = feats["ts"] < cutoff
    test_mask = ~train_mask

    model = GradientBoostingRegressor(random_state=42)
    model.fit(X[train_mask], y[train_mask])

    preds = model.predict(X[test_mask])
    y_true = y[test_mask]
    mae = float(mean_absolute_error(y_true, preds))
    mape = float(np.mean(np.abs((y_true - preds) / np.clip(y_true, 1e-6, None)))) * 100.0

    last_day = feats["ts"].max().floor("D")
    next_day = (last_day + pd.Timedelta(days=1)).to_pydatetime().replace(tzinfo=timezone.utc)

    forecast_rows = []
    for bid, g in feats.groupby("building_id"):
        g_last = g[g["day"] == last_day]
        if g_last.empty:
            continue
        for hour in range(24):
            ref = g_last[g_last["hour"] == hour].tail(1)
            if ref.empty:
                continue
            row = {
                "hour": hour,
                "dow": (pd.Timestamp(next_day).dayofweek),
                "total_energy_usage_lag_1": float(ref["total_energy_usage"].values[0]),
                "total_energy_usage_lag_24": float(ref["total_energy_usage_lag_24"].values[0]),
                "total_energy_usage_roll_24": float(ref["total_energy_usage_roll_24"].values[0]),
            }
            kwh_hat = float(model.predict(pd.DataFrame([row]))[0])
            forecast_rows.append({"ts": pd.Timestamp(next_day) + pd.Timedelta(hours=hour), "building_id": bid, "kwh_forecast": kwh_hat})

    fc = pd.DataFrame(forecast_rows)
    if fc.empty:
        daily_forecast = pd.DataFrame(columns=["day", "building_id", "kwh_forecast", "kwh_actual", "model_name"])
    else:
        daily_forecast = (
            fc.assign(day=fc["ts"].dt.floor("D"))
            .groupby(["day", "building_id"], as_index=False)["kwh_forecast"]
            .sum()
            .merge(
                feats.groupby([feats["ts"].dt.floor("D"), "building_id"], as_index=False)["total_energy_usage"].sum().rename(columns={"ts": "day", "total_energy_usage": "kwh_actual"}),
                on=["day", "building_id"],
                how="left",
            )
        )
        daily_forecast["model_name"] = "gbr_lag_features"

    result = ForecastResult(model_name="gbr_lag_features", mae=mae, mape=mape)
    return daily_forecast, result
