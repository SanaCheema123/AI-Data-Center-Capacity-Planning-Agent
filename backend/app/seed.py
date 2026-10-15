"""Seed reference/configuration records only.

This command intentionally does **not** create users, data centers, metrics, alerts,
forecasts, procurement costs, or reports. It is safe to run in a real-data
installation after migrations:

    python -m app.seed

Real infrastructure data must arrive through CSV import or configured collectors.
The first development user can register through the UI and is promoted to Admin
only when BOOTSTRAP_FIRST_USER_AS_ADMIN=true. Production administrators should
use ``python -m app.bootstrap_admin`` instead.
"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.domain import ForecastModel, Role, Scenario
from app.models.system_setting import SystemSetting

ROLES = {
    "Admin": "Full administrative access",
    "Infrastructure Planner": "Forecast, scenario, procurement, alert, and reporting operations",
    "Analyst": "Analysis, forecast, scenario, and reporting access",
    "Viewer": "Read-only dashboard access",
}


def seed() -> None:
    db = SessionLocal()
    try:
        roles = {}
        for name, description in ROLES.items():
            role = db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=description)
                db.add(role)
                db.flush()
            roles[name] = role

        if db.scalar(select(ForecastModel).where(ForecastModel.name == "Prophet")) is None:
            db.add(ForecastModel(name="Prophet", model_type="prophet", version="1.1", config={}, is_enabled=True))
        if db.scalar(select(ForecastModel).where(ForecastModel.name == "XGBoost")) is None:
            db.add(ForecastModel(name="XGBoost", model_type="xgboost", version="2.x", config={}, is_enabled=True))

        defaults = {
            "forecast": {"default_model": "prophet", "horizon_months": 12, "confidence_interval": 0.9},
            "capacity_thresholds": {"gpu": 80, "power": 85, "storage": 80, "network": 75},
            "data_mode": {"mode": "real", "synthetic_data_enabled": False},
        }
        for key, value in defaults.items():
            setting = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
            if setting is None:
                db.add(SystemSetting(key=key, value=value))
            elif key == "data_mode":
                setting.value = value

        # These are planning templates, not telemetry/demo results. Users may edit
        # or replace them before running scenario comparisons.
        templates = [
            ("Conservative", "conservative", "Efficiency-first planning template.", 0.90),
            ("Base Case", "base", "Current forecast baseline without additional demand uplift.", 1.00),
            ("Aggressive", "aggressive", "Stress-test template for higher workload growth.", 1.25),
        ]
        for name, kind, description, multiplier in templates:
            if db.scalar(select(Scenario).where(Scenario.name == name, Scenario.data_center_id.is_(None))) is None:
                db.add(Scenario(
                    name=name,
                    description=description,
                    scenario_type=kind,
                    planning_horizon_months=36,
                    assumptions={"growth_multiplier": multiplier, "template": True},
                    created_by=None,
                ))

        db.commit()
        print("Reference configuration initialized (no demo users or synthetic metrics created).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
