from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from app.forecasting.base import ForecastModel, ForecastPoint, ForecastRequest, ForecastSeries
from app.forecasting.utils import (
    accuracy_metrics,
    default_seasonal_period,
    future_index,
    holdout_size,
    interval_from_residual_std,
    sorted_series,
    validate_history,
)

try:  # Production Docker installs prophet. The local fallback keeps offline development runnable.
    from prophet import Prophet  # type: ignore
except Exception:  # pragma: no cover - depends on optional binary/runtime availability
    Prophet = None


def _trend_season_features(index: pd.DatetimeIndex, start: pd.Timestamp, period: int) -> np.ndarray:
    elapsed = np.asarray([(ts - start).days / 365.25 for ts in index], dtype=float)
    features = [np.ones(len(index)), elapsed]
    # Fourier terms approximate Prophet-style additive seasonality for offline fallback only.
    ordinal = np.arange(len(index), dtype=float)
    for k in (1, 2):
        features.append(np.sin(2 * np.pi * k * ordinal / period))
        features.append(np.cos(2 * np.pi * k * ordinal / period))
    return np.column_stack(features)


class ProphetForecastModel(ForecastModel):
    name = "prophet"

    def fit_predict(self, request: ForecastRequest) -> ForecastSeries:
        validate_history(request.history)
        series = sorted_series(request.history)
        if Prophet is not None:
            return self._native_prophet(series, request)
        return self._offline_fallback(series, request)

    def _native_prophet(self, series: pd.Series, request: ForecastRequest) -> ForecastSeries:
        frame = pd.DataFrame({"ds": series.index.tz_localize(None) if series.index.tz is not None else series.index, "y": series.values})
        holdout = holdout_size(len(frame))
        train = frame.iloc[:-holdout]
        evaluator = Prophet(interval_width=request.confidence, yearly_seasonality="auto", weekly_seasonality="auto", daily_seasonality=False)
        evaluator.fit(train)
        eval_fc = evaluator.predict(frame.iloc[-holdout:][["ds"]])
        metrics = accuracy_metrics(frame.iloc[-holdout:]["y"].tolist(), eval_fc["yhat"].tolist())

        model = Prophet(interval_width=request.confidence, yearly_seasonality="auto", weekly_seasonality="auto", daily_seasonality=False)
        model.fit(frame)
        dates = future_index(series.index[-1].to_pydatetime(), request.horizon, request.frequency)
        future = pd.DataFrame({"ds": dates.tz_localize(None) if dates.tz is not None else dates})
        forecast = model.predict(future)
        points = [
            ForecastPoint(
                timestamp=ts.to_pydatetime(),
                predicted=max(0.0, float(row.yhat)),
                lower=max(0.0, float(row.yhat_lower)),
                upper=max(0.0, float(row.yhat_upper)),
            )
            for ts, row in zip(dates, forecast.itertuples())
        ]
        return ForecastSeries(points=points, model_name=self.name, metrics=metrics, metadata={"engine": "prophet"})

    def _offline_fallback(self, series: pd.Series, request: ForecastRequest) -> ForecastSeries:
        period = request.seasonal_period or default_seasonal_period(request.frequency)
        holdout = holdout_size(len(series))
        train = series.iloc[:-holdout]
        eval_index = series.index[-holdout:]
        X_train = _trend_season_features(train.index, train.index[0], period)
        evaluator = Ridge(alpha=0.1).fit(X_train, train.values)
        # Keep the same feature basis length by building combined index then slicing.
        combined = train.index.append(eval_index)
        X_combined = _trend_season_features(combined, train.index[0], period)
        eval_pred = np.maximum(0.0, evaluator.predict(X_combined[-holdout:]))
        metrics = accuracy_metrics(series.iloc[-holdout:].values, eval_pred)
        residuals = series.iloc[-holdout:].values - eval_pred
        residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else metrics["rmse"]

        dates = future_index(series.index[-1].to_pydatetime(), request.horizon, request.frequency)
        combined_full = series.index.append(dates)
        X_full = _trend_season_features(series.index, series.index[0], period)
        model = Ridge(alpha=0.1).fit(X_full, series.values)
        X_future = _trend_season_features(combined_full, series.index[0], period)[-request.horizon:]
        predictions = np.maximum(0.0, model.predict(X_future))
        lower, upper = interval_from_residual_std(predictions, residual_std, request.confidence)
        points = [
            ForecastPoint(timestamp=ts.to_pydatetime(), predicted=float(pred), lower=float(lo), upper=float(hi))
            for ts, pred, lo, hi in zip(dates, predictions, lower, upper)
        ]
        return ForecastSeries(
            points=points,
            model_name=self.name,
            metrics={**metrics, "residual_std": residual_std},
            metadata={"engine": "prophet-compatible-offline-fallback", "seasonal_period": period},
        )
