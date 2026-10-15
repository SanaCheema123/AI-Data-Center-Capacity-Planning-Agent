from __future__ import annotations

from datetime import datetime
from math import ceil
from statistics import NormalDist
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from app.forecasting.base import ForecastPoint, TimePoint

FREQUENCY_MAP = {
    "daily": "D",
    "weekly": "W",
    "monthly": "MS",
    "D": "D",
    "W": "W",
    "MS": "MS",
}


def normalize_frequency(value: str) -> str:
    try:
        return FREQUENCY_MAP[value]
    except KeyError as exc:
        raise ValueError(f"Unsupported forecast frequency: {value}") from exc


def validate_history(history: Sequence[TimePoint], minimum: int = 8) -> None:
    if len(history) < minimum:
        raise ValueError("Insufficient data for reliable forecast.")
    timestamps = [p.timestamp for p in history]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("Forecast history contains duplicate timestamps.")
    if any(not np.isfinite(p.value) for p in history):
        raise ValueError("Forecast history contains non-finite values.")


def sorted_series(history: Sequence[TimePoint]) -> pd.Series:
    ordered = sorted(history, key=lambda x: x.timestamp)
    index = pd.DatetimeIndex([p.timestamp for p in ordered])
    return pd.Series([float(p.value) for p in ordered], index=index, dtype=float)


def future_index(last_timestamp: datetime, horizon: int, frequency: str) -> pd.DatetimeIndex:
    if horizon < 1:
        raise ValueError("Forecast horizon must be at least 1.")
    freq = normalize_frequency(frequency)
    start = pd.Timestamp(last_timestamp)
    if freq == "MS":
        first = start + pd.offsets.MonthBegin(1)
    elif freq == "W":
        first = start + pd.offsets.Week(1)
    else:
        first = start + pd.Timedelta(days=1)
    return pd.date_range(first, periods=horizon, freq=freq)


def confidence_z(confidence: float) -> float:
    if not 0.5 <= confidence < 1.0:
        raise ValueError("Confidence interval must be >= 0.5 and < 1.0.")
    return float(NormalDist().inv_cdf(0.5 + confidence / 2.0))


def interval_from_residual_std(predictions: Iterable[float], residual_std: float, confidence: float) -> tuple[np.ndarray, np.ndarray]:
    predictions_arr = np.asarray(list(predictions), dtype=float)
    margin = confidence_z(confidence) * max(float(residual_std), 1e-9)
    return np.maximum(0.0, predictions_arr - margin), predictions_arr + margin


def accuracy_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if len(y) == 0 or len(y) != len(p):
        return {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "r2": 0.0}
    errors = y - p
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    nonzero = np.abs(y) > 1e-9
    mape = float(np.mean(np.abs(errors[nonzero] / y[nonzero])) * 100.0) if np.any(nonzero) else 0.0
    ss_res = float(np.sum(errors**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else (1.0 if ss_res <= 1e-12 else 0.0)
    return {"mae": mae, "rmse": rmse, "mape": mape, "r2": float(r2)}


def peak_demand(points: Sequence[ForecastPoint]) -> ForecastPoint | None:
    return max(points, key=lambda p: p.predicted, default=None)


def shortage_date(points: Sequence[ForecastPoint], capacity: float | Sequence[float] | None) -> datetime | None:
    if capacity is None:
        return None
    if isinstance(capacity, (int, float)):
        capacities = [float(capacity)] * len(points)
    else:
        capacities = [float(v) for v in capacity]
        if len(capacities) != len(points):
            raise ValueError("Capacity series length must match forecast points.")
    for point, cap in zip(points, capacities):
        if point.predicted >= cap:
            return point.timestamp
    return None


def capacity_headroom(capacity: float, usage: float) -> float:
    return float(capacity) - float(usage)


def utilization_percent(usage: float, capacity: float) -> float:
    if capacity <= 0:
        raise ValueError("Capacity must be greater than zero.")
    return float(usage) / float(capacity) * 100.0


def required_expansion(peak: float, capacity: float, target_utilization: float = 1.0) -> float:
    if not 0 < target_utilization <= 1:
        raise ValueError("Target utilization must be within (0, 1].")
    target_capacity = float(peak) / target_utilization
    return max(0.0, target_capacity - float(capacity))


def default_seasonal_period(frequency: str) -> int:
    freq = normalize_frequency(frequency)
    if freq == "D":
        return 7
    if freq == "W":
        return 52
    return 12


def holdout_size(n: int) -> int:
    return max(2, min(6, ceil(n * 0.2)))
