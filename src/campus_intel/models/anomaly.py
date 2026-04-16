from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AnomalyMetrics:
    precision: float
    recall: float
    f1: float


def _robust_zscore(x: pd.Series, window: int = 24 * 7) -> pd.Series:
    med = x.rolling(window, min_periods=max(6, window // 4)).median()
    mad = (x - med).abs().rolling(window, min_periods=max(6, window // 4)).median()
    mad = mad.replace(0, np.nan)
    z = 0.6745 * (x - med) / mad
    return z.fillna(0.0)


def detect_anomalies(
    df: pd.DataFrame,
    entity_type: str,
    entity_col: str,
    metric: str,
    z_threshold: float = 4.0,
) -> pd.DataFrame:
    """
    Robust z-score anomaly detection.
    Returns rows: ts, entity_type, entity_id, metric, value, score, is_anomaly, reason
    """
    d = df[[ "ts", entity_col, metric]].copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    d = d.sort_values([entity_col, "ts"])

    out_frames = []
    for eid, g in d.groupby(entity_col):
        g = g.copy()
        g["score"] = _robust_zscore(g[metric])
        g["is_anomaly"] = (g["score"].abs() >= z_threshold).astype(int)
        g["entity_type"] = entity_type
        g["entity_id"] = eid
        g["metric"] = metric
        g["value"] = g[metric].astype(float)
        g["reason"] = np.where(g["is_anomaly"] == 1, f"robust_z>= {z_threshold}", "normal")
        out_frames.append(g[["ts", "entity_type", "entity_id", "metric", "value", "score", "is_anomaly", "reason"]])

    out = pd.concat(out_frames, ignore_index=True)
    out["ts"] = out["ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


def score_against_injected(anomalies: pd.DataFrame, injected_labels: list[dict]) -> AnomalyMetrics:
    """
    Evaluate precision/recall on injected spike labels (only for matching entity_type/entity_id/metric/ts).
    """
    if not injected_labels:
        return AnomalyMetrics(precision=0.0, recall=0.0, f1=0.0)

    truth = pd.DataFrame(injected_labels)[["ts", "entity_type", "entity_id", "metric"]].drop_duplicates()
    pred = anomalies[["ts", "entity_type", "entity_id", "metric", "is_anomaly"]].copy()
    pred = pred[pred["is_anomaly"] == 1][["ts", "entity_type", "entity_id", "metric"]].drop_duplicates()

    truth_keys = set(map(tuple, truth.values.tolist()))
    pred_keys = set(map(tuple, pred.values.tolist()))

    tp = len(truth_keys & pred_keys)
    fp = len(pred_keys - truth_keys)
    fn = len(truth_keys - pred_keys)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    return AnomalyMetrics(precision=float(precision), recall=float(recall), f1=float(f1))

