import pytest

from app.forecasting.base import ForecastModel, ForecastRequest, ForecastSeries
from app.forecasting.registry import ForecastModelRegistry


class ExampleModel(ForecastModel):
    name = "example"

    def fit_predict(self, request: ForecastRequest) -> ForecastSeries:
        return ForecastSeries(points=[], model_name=self.name, metrics={})


def test_registry_registers_model() -> None:
    registry = ForecastModelRegistry()
    registry.register(ExampleModel)
    assert registry.available() == ("example",)
    assert isinstance(registry.create("example"), ExampleModel)


def test_unknown_model_is_explicit() -> None:
    registry = ForecastModelRegistry()
    with pytest.raises(ValueError, match="Unknown forecast model"):
        registry.create("missing")
