from __future__ import annotations

import numpy as np
from xgboost import XGBRegressor

from app.forecasting.base import ForecastModel, ForecastPoint, ForecastRequest, ForecastSeries
from app.forecasting.features import next_feature, supervised_features
from app.forecasting.utils import (
    accuracy_metrics,
    future_index,
    holdout_size,
    interval_from_residual_std,
    sorted_series,
    validate_history,
)


class XGBoostForecastModel(ForecastModel):
    name = "xgboost"

    @staticmethod
    def _model() -> XGBRegressor:
        return XGBRegressor(
            n_estimators=250,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=1,
        )

    def _recursive(self, model: XGBRegressor, values: list[float], dates, steps: int, lag_count: int) -> list[float]:
        predictions: list[float] = []
        work = list(values)
        base_index = len(values)
        for step in range(steps):
            feature = next_feature(work, dates[step], base_index + step, lag_count)
            value = max(0.0, float(model.predict(feature)[0]))
            predictions.append(value)
            work.append(value)
        return predictions

    def fit_predict(self, request: ForecastRequest) -> ForecastSeries:
        validate_history(request.history)
        series = sorted_series(request.history)
        values = series.to_numpy(dtype=float)
        lag_count = min(3, max(1, len(values) // 5))

        # Time-ordered holdout for honest accuracy metrics and interval calibration.
        holdout = holdout_size(len(values))
        train_values = values[:-holdout]
        train_dates = series.index[:-holdout]
        X_train, y_train = supervised_features(train_values, train_dates, lag_count)
        if len(X_train) < 2:
            raise ValueError("Insufficient data for reliable forecast.")
        eval_model = self._model()
        eval_model.fit(X_train, y_train)
        eval_dates = series.index[-holdout:]
        eval_pred = self._recursive(eval_model, list(train_values), eval_dates, holdout, lag_count)
        metrics = accuracy_metrics(values[-holdout:], eval_pred)
        residual_std = float(np.std(values[-holdout:] - np.asarray(eval_pred), ddof=1)) if holdout > 1 else metrics["rmse"]

        X_full, y_full = supervised_features(values, series.index, lag_count)
        model = self._model()
        model.fit(X_full, y_full)
        dates = future_index(series.index[-1].to_pydatetime(), request.horizon, request.frequency)
        predictions = self._recursive(model, list(values), dates, request.horizon, lag_count)
        lower, upper = interval_from_residual_std(predictions, residual_std, request.confidence)

        points = [
            ForecastPoint(timestamp=ts.to_pydatetime(), predicted=float(pred), lower=float(lo), upper=float(hi))
            for ts, pred, lo, hi in zip(dates, predictions, lower, upper)
        ]
        return ForecastSeries(
            points=points,
            model_name=self.name,
            metrics={**metrics, "residual_std": residual_std},
            metadata={"engine": "xgboost", "lag_count": lag_count},
        )
