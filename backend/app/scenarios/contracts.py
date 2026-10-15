from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioAssumptions:
    gpu_growth_rate: float
    storage_growth_rate: float
    network_growth_rate: float
    power_efficiency_factor: float
    planning_horizon_months: int
    budget_limit: float | None = None
