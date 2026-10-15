"""Remove legacy synthetic/demo records created by older project versions.

This is intentionally explicit and opt-in. It only targets records that can be
identified by the legacy demo markers/accounts shipped by earlier builds.

Usage:
    python -m app.purge_demo_data --yes

Run this once when upgrading an existing database that was previously seeded
with synthetic demo telemetry.
"""
from __future__ import annotations

import argparse

from sqlalchemy import delete, or_, select

from app.db.session import SessionLocal
from app.models.domain import (
    Alert, AlertEvent, AuditLog, Cluster, DataCenter, DataSource, ForecastResult,
    ForecastRun, InfrastructureMetric, NotificationSetting, ProcurementRecommendation,
    Report, Scenario, ScenarioResult, User, UserPreference, user_roles,
)

LEGACY_DEMO_EMAILS = {"admin@example.com", "planner@example.com"}


def purge() -> dict[str, int]:
    db = SessionLocal()
    counts: dict[str, int] = {}
    try:
        demo_users = list(db.scalars(select(User).where(User.email.in_(LEGACY_DEMO_EMAILS))))
        user_ids = [u.id for u in demo_users]
        demo_dcs = [dc for dc in db.scalars(select(DataCenter)) if (dc.meta or {}).get("dataset") == "demo"]
        dc_ids = [dc.id for dc in demo_dcs]
        demo_sources = [s for s in db.scalars(select(DataSource)) if (s.configuration or {}).get("demo") is True or s.name.startswith("Demo ")]
        source_ids = [s.id for s in demo_sources]

        forecast_conditions = []
        if dc_ids:
            forecast_conditions.append(ForecastRun.data_center_id.in_(dc_ids))
        if user_ids:
            forecast_conditions.append(ForecastRun.requested_by.in_(user_ids))
        forecast_ids = [r.id for r in db.scalars(select(ForecastRun).where(or_(*forecast_conditions)))] if forecast_conditions else []
        alert_ids = [a.id for a in db.scalars(select(Alert).where(Alert.data_center_id.in_(dc_ids)))] if dc_ids else []
        scenario_conditions = []
        if dc_ids:
            scenario_conditions.append(Scenario.data_center_id.in_(dc_ids))
        if user_ids:
            scenario_conditions.append(Scenario.created_by.in_(user_ids))
        scenario_ids = [s.id for s in db.scalars(select(Scenario).where(or_(*scenario_conditions)))] if scenario_conditions else []

        def do(name: str, stmt) -> None:
            result = db.execute(stmt)
            counts[name] = int(result.rowcount or 0)

        if alert_ids:
            do("alert_events", delete(AlertEvent).where(AlertEvent.alert_id.in_(alert_ids)))
        if user_ids:
            do("alert_events_by_user", delete(AlertEvent).where(AlertEvent.actor_user_id.in_(user_ids)))
        if dc_ids:
            do("alerts", delete(Alert).where(Alert.data_center_id.in_(dc_ids)))
            do("procurement", delete(ProcurementRecommendation).where(ProcurementRecommendation.data_center_id.in_(dc_ids)))
            do("reports_by_dc", delete(Report).where(Report.data_center_id.in_(dc_ids)))
        if forecast_ids:
            do("forecast_results", delete(ForecastResult).where(ForecastResult.forecast_run_id.in_(forecast_ids)))
            do("procurement_by_forecast", delete(ProcurementRecommendation).where(ProcurementRecommendation.forecast_run_id.in_(forecast_ids)))
            do("forecast_runs", delete(ForecastRun).where(ForecastRun.id.in_(forecast_ids)))
        if scenario_ids:
            do("scenario_results", delete(ScenarioResult).where(ScenarioResult.scenario_id.in_(scenario_ids)))
            do("scenarios", delete(Scenario).where(Scenario.id.in_(scenario_ids)))
        if dc_ids or source_ids:
            criteria = []
            if dc_ids:
                criteria.append(InfrastructureMetric.data_center_id.in_(dc_ids))
            if source_ids:
                criteria.append(InfrastructureMetric.source_id.in_(source_ids))
            expr = criteria[0]
            for c in criteria[1:]:
                expr = expr | c
            do("metrics", delete(InfrastructureMetric).where(expr))
        if dc_ids:
            do("clusters", delete(Cluster).where(Cluster.data_center_id.in_(dc_ids)))
            do("data_centers", delete(DataCenter).where(DataCenter.id.in_(dc_ids)))
        if source_ids:
            do("data_sources", delete(DataSource).where(DataSource.id.in_(source_ids)))
        if user_ids:
            do("notification_settings", delete(NotificationSetting).where(NotificationSetting.user_id.in_(user_ids)))
            do("user_preferences", delete(UserPreference).where(UserPreference.user_id.in_(user_ids)))
            do("reports_by_user", delete(Report).where(Report.owner_id.in_(user_ids)))
            do("audit_logs", delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
            do("user_roles", delete(user_roles).where(user_roles.c.user_id.in_(user_ids)))
            do("users", delete(User).where(User.id.in_(user_ids)))

        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove legacy synthetic/demo records")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive cleanup")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("Refusing to modify the database without --yes")
    counts = purge()
    total = sum(counts.values())
    print(f"Legacy demo cleanup complete. Removed {total} rows.")
    for name, count in sorted(counts.items()):
        if count:
            print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
