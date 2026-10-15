from __future__ import annotations

import numpy as np
import pandas as pd


def supervised_features(values: np.ndarray, timestamps: pd.DatetimeIndex, lag_count: int = 3) -> tuple[np.ndarray, np.ndarray]:
    rows: list[list[float]] = []
    targets: list[float] = []
    lag_count = max(1, min(lag_count, len(values) - 2))
    for i in range(lag_count, len(values)):
        ts = timestamps[i]
        lags = [float(values[i - j]) for j in range(1, lag_count + 1)]
        history = values[max(0, i - 6):i]
        row = lags + [
            float(np.mean(history)),
            float(np.std(history)) if len(history) > 1 else 0.0,
            float(i),
            float(ts.month),
            float(np.sin(2 * np.pi * ts.month / 12.0)),
            float(np.cos(2 * np.pi * ts.month / 12.0)),
        ]
        rows.append(row)
        targets.append(float(values[i]))
    return np.asarray(rows, dtype=float), np.asarray(targets, dtype=float)


def next_feature(values: list[float], timestamp: pd.Timestamp, step_index: int, lag_count: int = 3) -> np.ndarray:
    lag_count = max(1, min(lag_count, len(values)))
    lags = [float(values[-j]) for j in range(1, lag_count + 1)]
    while len(lags) < lag_count:
        lags.append(lags[-1])
    history = np.asarray(values[-6:], dtype=float)
    row = lags + [
        float(np.mean(history)),
        float(np.std(history)) if len(history) > 1 else 0.0,
        float(step_index),
        float(timestamp.month),
        float(np.sin(2 * np.pi * timestamp.month / 12.0)),
        float(np.cos(2 * np.pi * timestamp.month / 12.0)),
    ]
    return np.asarray(row, dtype=float).reshape(1, -1)
