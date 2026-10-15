from app.forecasting.base import ForecastModel
from app.forecasting.models import ProphetForecastModel, XGBoostForecastModel


class ForecastModelRegistry:
    def __init__(self, include_defaults: bool = False) -> None:
        self._models: dict[str, type[ForecastModel]] = {}
        if include_defaults:
            self.register(ProphetForecastModel)
            self.register(XGBoostForecastModel)

    def register(self, model: type[ForecastModel]) -> None:
        self._models[model.name.lower()] = model

    def create(self, name: str) -> ForecastModel:
        try:
            model_type = self._models[name.lower()]
        except KeyError as exc:
            raise ValueError(f"Unknown forecast model: {name}") from exc
        return model_type()

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(self._models))


def default_registry() -> ForecastModelRegistry:
    return ForecastModelRegistry(include_defaults=True)
