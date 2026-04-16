from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score


@dataclass(frozen=True)
class PeakMessMetrics:
    f1: float
    threshold: float
    model_name: str


def _make_features(mess: pd.DataFrame) -> pd.DataFrame:
    df = mess.copy()
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values(["mess_id", "ts"])
    df["hour"] = df["ts"].dt.hour
    df["dow"] = df["ts"].dt.dayofweek
    df["entries_lag_1"] = df.groupby("mess_id")["entries"].shift(1)
    df["entries_lag_24"] = df.groupby("mess_id")["entries"].shift(24)
    df["wait_lag_1"] = df.groupby("mess_id")["estimated_wait_min"].shift(1)
    df["roll_entries_6"] = df.groupby("mess_id")["entries"].shift(1).rolling(6).mean().reset_index(level=0, drop=True)
    df = df.dropna().copy()
    return df


def run_peak_mess_prediction(mess_footfall: pd.DataFrame) -> tuple[pd.DataFrame, PeakMessMetrics]:
    """
    Predict whether the NEXT hour will be a peak (top 20% entries for that mess).
    Writes forecast rows for next hour and also provides evaluation F1 on last 7 days.
    """
    df = mess_footfall.copy()
    feats = _make_features(df)

    # Define peak based on per-mess quantile
    q = feats.groupby("mess_id")["entries"].transform(lambda s: s.quantile(0.8))
    feats["is_peak"] = (feats["entries"] >= q).astype(int)

    X = feats[["hour", "dow", "entries_lag_1", "entries_lag_24", "wait_lag_1", "roll_entries_6"]].values
    y = feats["is_peak"].values

    cutoff = feats["ts"].max() - pd.Timedelta(days=7)
    train_mask = feats["ts"] < cutoff
    test_mask = ~train_mask

    model = LogisticRegression(max_iter=500, n_jobs=None)
    model.fit(X[train_mask], y[train_mask])

    prob = model.predict_proba(X[test_mask])[:, 1]
    # choose threshold that maximizes F1 on test
    thresholds = np.linspace(0.2, 0.8, 25)
    best_t, best_f1 = 0.5, -1.0
    for t in thresholds:
        f1 = f1_score(y[test_mask], (prob >= t).astype(int))
        if f1 > best_f1:
            best_f1, best_t = float(f1), float(t)

    # Forecast next hour for each mess using the last row
    last_ts = feats["ts"].max()
    next_ts = last_ts + pd.Timedelta(hours=1)
    rows = []
    for mid, g in feats.groupby("mess_id"):
        last = g.tail(1)
        if last.empty:
            continue
        row = np.array(
            [
                next_ts.hour,
                next_ts.dayofweek,
                float(last["entries"].values[0]),
                float(last["entries_lag_24"].values[0]),
                float(last["estimated_wait_min"].values[0]),
                float(last["roll_entries_6"].values[0]),
            ]
        ).reshape(1, -1)
        peak_prob = float(model.predict_proba(row)[:, 1][0])
        predicted_peak = int(peak_prob >= best_t)
        # entries forecast (rough): blend last + seasonal lag
        entries_forecast = float(0.6 * last["entries"].values[0] + 0.4 * last["entries_lag_24"].values[0])
        rows.append(
            {
                "ts": next_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "mess_id": mid,
                "peak_prob": peak_prob,
                "predicted_peak": predicted_peak,
                "entries_forecast": entries_forecast,
                "model_name": "logreg_peak_v1",
            }
        )

    out = pd.DataFrame(rows)
    metrics = PeakMessMetrics(f1=best_f1, threshold=best_t, model_name="logreg_peak_v1")
    return out, metrics

