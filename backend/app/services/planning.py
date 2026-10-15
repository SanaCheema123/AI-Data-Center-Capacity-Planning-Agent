from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.domain import (
    Alert,
    DataSource,
    ForecastRun,
    ProcurementItem,
    ProcurementRecommendation,
    Report,
    Scenario,
    ScenarioResult,
    User,
)
from app.models.system_setting import SystemSetting
from app.schemas.planning import RecommendationRead, ScenarioComparison
from app.services.data_scope import real_data_center_ids
from app.services.forecasting import ForecastingService


RESOURCE_UNITS = {
    "gpu": "GPUs",
    "power": "MW",
    "storage": "TB",
    "network": "Gbps",
}

RESOURCE_LABELS = {
    "gpu": "GPU",
    "power": "power",
    "storage": "storage",
    "network": "network",
}

DEFAULT_THRESHOLDS = {
    "gpu": 80.0,
    "power": 85.0,
    "storage": 80.0,
    "network": 75.0,
}


def _capacity_thresholds(db: Session) -> dict[str, float]:
    """
    Return normalized capacity-planning thresholds.

    Stored settings override the defaults, but invalid/missing values
    never break the planning workflow.
    """
    setting = db.scalar(
        select(SystemSetting).where(
            SystemSetting.key == "capacity_thresholds"
        )
    )

    raw = (setting.value if setting else {}) or {}

    thresholds: dict[str, float] = {}

    for resource, default in DEFAULT_THRESHOLDS.items():
        try:
            value = float(raw.get(resource, default))
        except (TypeError, ValueError):
            value = default

        # Prevent impossible planning values.
        thresholds[resource] = max(1.0, min(value, 100.0))

    return thresholds


def _forecast_utilization(peak: float, capacity: float) -> float:
    if capacity <= 0:
        return 0.0
    return (peak / capacity) * 100.0


def _planning_capacity(
    peak: float,
    current_capacity: float,
    threshold_pct: float,
) -> tuple[float, float, float]:
    """
    Returns:
        forecast_utilization_pct
        required_capacity
        planning_gap

    Example:
        peak = 452
        capacity = 500
        threshold = 75%

        forecast utilization = 90.4%
        required capacity = 452 / .75 = 602.67
        planning gap = 102.67
    """
    if current_capacity <= 0:
        return 0.0, current_capacity, 0.0

    target_utilization = max(threshold_pct / 100.0, 0.01)
    forecast_util = _forecast_utilization(peak, current_capacity)

    if forecast_util < threshold_pct:
        return forecast_util, current_capacity, 0.0

    required_capacity = peak / target_utilization
    planning_gap = max(0.0, required_capacity - current_capacity)

    return forecast_util, required_capacity, planning_gap


def _severity_from_threshold(
    forecast_utilization: float,
    threshold: float,
) -> str:
    """
    Severity is based on both:
    1. Physical exhaustion
    2. Distance above the configured planning threshold

    This keeps Alerts consistent with user-configured thresholds.
    """
    over_threshold = forecast_utilization - threshold

    if forecast_utilization >= 100.0:
        return "critical"

    if over_threshold >= 15.0:
        return "high"

    if over_threshold >= 7.5:
        return "medium"

    return "low"


def _planning_deadline(
    shortage_date: datetime | None,
    forecast_utilization: float,
    threshold: float,
) -> datetime:
    """
    A physical shortage date is preferred when available.

    If forecast utilization has already breached the planning threshold,
    create a proactive procurement deadline before physical exhaustion.
    """
    now = datetime.now(timezone.utc)

    if shortage_date is not None:
        if shortage_date.tzinfo is None:
            shortage_date = shortage_date.replace(tzinfo=timezone.utc)
        return shortage_date

    over_threshold = forecast_utilization - threshold

    if forecast_utilization >= 100.0 or over_threshold >= 20.0:
        return now + timedelta(days=60)

    if over_threshold >= 15.0:
        return now + timedelta(days=90)

    if over_threshold >= 7.5:
        return now + timedelta(days=180)

    return now + timedelta(days=365)


class ScenarioService:
    @staticmethod
    def compare(
        db: Session,
        data_center_id: int | None = None,
        persist: bool = False,
    ) -> list[ScenarioComparison]:
        forecasts = {}

        for resource in RESOURCE_UNITS:
            try:
                forecasts[resource] = ForecastingService.latest(
                    db,
                    resource,
                    data_center_id,
                )
            except Exception:
                return []

        scenario_stmt = select(Scenario)

        if data_center_id is None:
            scenario_stmt = scenario_stmt.where(
                Scenario.data_center_id.is_(None)
            )
        else:
            scenario_stmt = scenario_stmt.where(
                (Scenario.data_center_id == data_center_id)
                | (Scenario.data_center_id.is_(None))
            )

        scenarios = list(
            db.scalars(
                scenario_stmt.order_by(Scenario.id)
            )
        )

        output: list[ScenarioComparison] = []

        for scenario in scenarios:
            assumptions = scenario.assumptions or {}

            growth = float(
                assumptions.get("growth_multiplier", 1.0)
            )

            gpu_multiplier = float(
                assumptions.get("gpu_multiplier", growth)
            )

            power_multiplier = float(
                assumptions.get("power_multiplier", growth)
            )

            storage_multiplier = float(
                assumptions.get("storage_multiplier", growth)
            )

            network_multiplier = float(
                assumptions.get("network_multiplier", growth)
            )

            gpu = (
                forecasts["gpu"].capacity.peak_demand
                * gpu_multiplier
            )

            power = (
                forecasts["power"].capacity.peak_demand
                * power_multiplier
            )

            storage = (
                forecasts["storage"].capacity.peak_demand
                * storage_multiplier
            )

            network = (
                forecasts["network"].capacity.peak_demand
                * network_multiplier
            )

            ratios = [
                gpu
                / max(
                    forecasts["gpu"].capacity.current_capacity,
                    1e-9,
                ),
                power
                / max(
                    forecasts["power"].capacity.current_capacity,
                    1e-9,
                ),
                storage
                / max(
                    forecasts["storage"].capacity.current_capacity,
                    1e-9,
                ),
                network
                / max(
                    forecasts["network"].capacity.current_capacity,
                    1e-9,
                ),
            ]

            risk_score = max(ratios) * 100

            risk_level = (
                "high"
                if risk_score >= 100
                else "medium"
                if risk_score >= 85
                else "low"
            )

            capex_per_unit = assumptions.get(
                "capex_per_unit",
                {},
            )

            capex = 0.0
            has_cost = False

            for resource, demand in [
                ("gpu", gpu),
                ("power", power),
                ("storage", storage),
                ("network", network),
            ]:
                current = (
                    forecasts[resource]
                    .capacity.current_capacity
                )

                gap = max(
                    0.0,
                    demand - current,
                )

                rate = capex_per_unit.get(resource)

                if rate is not None:
                    has_cost = True
                    capex += gap * float(rate)

            item = ScenarioComparison(
                id=scenario.id,
                name=scenario.name,
                scenario_type=scenario.scenario_type,
                description=scenario.description,
                planning_horizon_months=(
                    scenario.planning_horizon_months
                ),
                risk_level=risk_level,
                risk_score=round(risk_score, 2),
                gpu_demand=round(gpu, 2),
                power_demand_mw=round(power, 2),
                storage_demand_tb=round(storage, 2),
                network_demand_gbps=round(network, 2),
                estimated_capex=(
                    round(capex, 2)
                    if has_cost
                    else None
                ),
                assumptions=assumptions,
            )

            output.append(item)

            if persist:
                db.execute(
                    delete(ScenarioResult).where(
                        ScenarioResult.scenario_id
                        == scenario.id
                    )
                )

                db.add(
                    ScenarioResult(
                        scenario_id=scenario.id,
                        period=(
                            f"{scenario.planning_horizon_months} "
                            "months"
                        ),
                        gpu_demand=gpu,
                        power_demand_mw=power,
                        storage_demand_tb=storage,
                        network_demand_gbps=network,
                        shortage_risk=risk_score,
                        estimated_capex=(
                            capex
                            if has_cost
                            else None
                        ),
                        assumptions=assumptions,
                    )
                )

        if persist:
            db.commit()

        return output


class ProcurementService:
    @staticmethod
    def generate(
        db: Session,
        data_center_id: int | None = None,
    ) -> list[ProcurementRecommendation]:
        """
        Procurement is threshold-aware.

        A plan is created when forecast utilization breaches the
        configured planning threshold, even if physical capacity
        has not yet reached 100%.
        """
        thresholds = _capacity_thresholds(db)

        catalogs = {
            item.category: item
            for item in db.scalars(
                select(ProcurementItem)
            )
        }

        scope_expr = (
            ProcurementRecommendation.data_center_id.is_(None)
            if data_center_id is None
            else (
                ProcurementRecommendation.data_center_id
                == data_center_id
            )
        )

        existing = {
            item.resource_type: item
            for item in db.scalars(
                select(ProcurementRecommendation).where(
                    scope_expr
                )
            )
        }

        required_resources: set[str] = set()

        for resource in RESOURCE_UNITS:
            try:
                forecast = ForecastingService.latest(
                    db,
                    resource,
                    data_center_id,
                )
            except Exception:
                continue

            current_capacity = float(
                forecast.capacity.current_capacity or 0
            )

            peak_demand = float(
                forecast.capacity.peak_demand or 0
            )

            if current_capacity <= 0:
                continue

            threshold = float(
                thresholds.get(
                    resource,
                    DEFAULT_THRESHOLDS[resource],
                )
            )

            (
                forecast_utilization,
                required_capacity,
                planning_gap,
            ) = _planning_capacity(
                peak_demand,
                current_capacity,
                threshold,
            )

            # No procurement required while still safely
            # below the configured planning threshold.
            if planning_gap <= 0:
                continue

            required_resources.add(resource)

            catalog = catalogs.get(resource)

            unit_capacity = (
                float(catalog.unit_capacity)
                if catalog
                and catalog.unit_capacity
                else 1.0
            )

            quantity = ceil(
                planning_gap / unit_capacity
            )

            cost = (
                quantity * float(catalog.unit_cost)
                if catalog
                and catalog.unit_cost is not None
                else None
            )

            required_by = _planning_deadline(
                forecast.capacity.shortage_date,
                forecast_utilization,
                threshold,
            )

            days = (
                required_by
                - datetime.now(timezone.utc)
            ).days

            computed_priority = (
                "high"
                if days <= 180
                else "medium"
                if days <= 365
                else "low"
            )

            obj = existing.get(resource)

            if obj is None:
                obj = ProcurementRecommendation(
                    data_center_id=data_center_id,
                    resource_type=resource,
                    status="planned",
                    priority=computed_priority,
                )
                db.add(obj)

            obj.forecast_run_id = forecast.run_id
            obj.item_id = (
                catalog.id
                if catalog
                else None
            )

            obj.current_capacity = current_capacity
            obj.required_capacity = required_capacity
            obj.quantity = float(quantity)
            obj.required_by = required_by

            # Keep manually adjusted priority once an item
            # advances beyond the initial planned state.
            if obj.status == "planned":
                obj.priority = computed_priority

            obj.estimated_cost = cost

            physical_shortage = (
                forecast.capacity.required_expansion
                and forecast.capacity.required_expansion > 0
            )

            if physical_shortage:
                obj.reason = (
                    f"Forecast demand reaches "
                    f"{peak_demand:.1f} {forecast.unit}, "
                    f"which exceeds current physical capacity "
                    f"of {current_capacity:.1f} {forecast.unit}. "
                    f"Recommended planning capacity is "
                    f"{required_capacity:.1f} {forecast.unit} "
                    f"to restore headroom at the configured "
                    f"{threshold:.0f}% threshold."
                )
            else:
                obj.reason = (
                    f"Forecast utilization reaches "
                    f"{forecast_utilization:.1f}% against "
                    f"the configured {threshold:.0f}% "
                    f"planning threshold. "
                    f"Recommended capacity is "
                    f"{required_capacity:.1f} "
                    f"{forecast.unit}, requiring approximately "
                    f"{planning_gap:.1f} {forecast.unit} "
                    f"of additional headroom."
                )

        # Preserve approved/order history.
        # Only auto-complete untouched planned items.
        for resource, obj in existing.items():
            if (
                resource not in required_resources
                and obj.status == "planned"
            ):
                obj.status = "completed"
                obj.reason = (
                    "Latest forecast is below the configured "
                    "planning threshold and no additional "
                    "capacity is currently required."
                )

        db.commit()

        stmt = (
            select(ProcurementRecommendation)
            .where(scope_expr)
            .order_by(
                ProcurementRecommendation.created_at.desc()
            )
        )

        return list(db.scalars(stmt))


class AlertService:
    @staticmethod
    def evaluate(
        db: Session,
        data_center_id: int | None = None,
    ) -> list[Alert]:
        from app.models.domain import AlertEvent

        thresholds = _capacity_thresholds(db)

        # All Data Centers:
        # evaluate only real telemetry scopes.
        if data_center_id is None:
            dc_ids = real_data_center_ids(db)

            for dc_id in dc_ids:
                AlertService.evaluate(
                    db,
                    dc_id,
                )

            if not dc_ids:
                return []

            return list(
                db.scalars(
                    select(Alert)
                    .where(
                        Alert.data_center_id.in_(
                            dc_ids
                        )
                    )
                    .order_by(
                        Alert.triggered_at.desc()
                    )
                )
            )

        for resource in RESOURCE_UNITS:
            try:
                forecast = ForecastingService.latest(
                    db,
                    resource,
                    data_center_id,
                )
            except Exception:
                continue

            current_capacity = float(
                forecast.capacity.current_capacity or 0
            )

            peak = float(
                forecast.capacity.peak_demand or 0
            )

            if current_capacity <= 0:
                continue

            threshold = float(
                thresholds.get(
                    resource,
                    DEFAULT_THRESHOLDS[resource],
                )
            )

            forecast_util = _forecast_utilization(
                peak,
                current_capacity,
            )

            dedupe = (
                f"capacity:{data_center_id}:{resource}"
            )

            existing = db.scalar(
                select(Alert)
                .where(
                    Alert.dedupe_key == dedupe
                )
                .order_by(
                    Alert.id.desc()
                )
                .limit(1)
            )

            # Forecast has returned to a safe level.
            if forecast_util < threshold:
                if (
                    existing
                    and existing.status != "resolved"
                ):
                    old_status = existing.status

                    existing.status = "resolved"
                    existing.resolved_at = (
                        datetime.now(timezone.utc)
                    )

                    db.add(
                        AlertEvent(
                            alert_id=existing.id,
                            event_type="auto_resolved",
                            metadata_json={
                                "old": old_status,
                                "forecast_utilization": (
                                    forecast_util
                                ),
                                "threshold": threshold,
                            },
                        )
                    )

                continue

            severity = _severity_from_threshold(
                forecast_util,
                threshold,
            )

            description = (
                f"Forecast utilization reaches "
                f"{forecast_util:.1f}% against a configured "
                f"{threshold:.0f}% planning threshold."
            )

            if existing:
                if existing.status == "resolved":
                    existing.status = "open"
                    existing.resolved_at = None
                    existing.triggered_at = (
                        datetime.now(timezone.utc)
                    )

                    db.add(
                        AlertEvent(
                            alert_id=existing.id,
                            event_type="auto_reopened",
                            metadata_json={
                                "forecast_utilization": (
                                    forecast_util
                                ),
                                "threshold": threshold,
                            },
                        )
                    )

                existing.severity = severity
                existing.description = description
                existing.current_value = (
                    forecast.capacity.current_usage
                )
                existing.threshold_value = threshold
                existing.forecast_value = (
                    forecast.capacity.peak_demand
                )
                existing.predicted_shortage_at = (
                    forecast.capacity.shortage_date
                )

            else:
                db.add(
                    Alert(
                        data_center_id=data_center_id,
                        resource_type=resource,
                        severity=severity,
                        title=(
                            f"{RESOURCE_LABELS[resource].title()} "
                            "capacity risk"
                        ),
                        description=description,
                        current_value=(
                            forecast.capacity.current_usage
                        ),
                        threshold_value=threshold,
                        forecast_value=(
                            forecast.capacity.peak_demand
                        ),
                        predicted_shortage_at=(
                            forecast.capacity.shortage_date
                        ),
                        status="open",
                        dedupe_key=dedupe,
                        triggered_at=(
                            datetime.now(timezone.utc)
                        ),
                    )
                )

        db.commit()

        return list(
            db.scalars(
                select(Alert)
                .where(
                    Alert.data_center_id
                    == data_center_id
                )
                .order_by(
                    Alert.triggered_at.desc()
                )
            )
        )


class RecommendationService:
    @staticmethod
    def list(
        db: Session,
        data_center_id: int | None = None,
    ) -> list[RecommendationRead]:
        """
        Recommendations use exactly the same capacity thresholds
        as Alerts and Procurement.

        This prevents contradictions such as:
        Alert: Network risk at 90%
        AI: Maintain current network capacity
        """
        recommendations: list[RecommendationRead] = []

        thresholds = _capacity_thresholds(db)

        dependencies = {
            "gpu": [
                "power capacity",
                "cooling",
                "network throughput",
            ],
            "power": [
                "utility / electrical infrastructure",
                "cooling",
            ],
            "storage": [
                "storage fabric",
                "rack space",
            ],
            "network": [
                "switching capacity",
                "uplinks",
            ],
        }

        for resource in RESOURCE_UNITS:
            try:
                forecast = ForecastingService.latest(
                    db,
                    resource,
                    data_center_id,
                )
            except Exception:
                continue

            current_capacity = float(
                forecast.capacity.current_capacity or 0
            )

            peak = float(
                forecast.capacity.peak_demand or 0
            )

            if current_capacity <= 0:
                continue

            threshold = float(
                thresholds.get(
                    resource,
                    DEFAULT_THRESHOLDS[resource],
                )
            )

            (
                forecast_utilization,
                required_capacity,
                planning_gap,
            ) = _planning_capacity(
                peak,
                current_capacity,
                threshold,
            )

            physical_shortage = (
                forecast.capacity.required_expansion
                and forecast.capacity.required_expansion > 0
            )

            threshold_breached = (
                forecast_utilization >= threshold
            )

            if physical_shortage:
                recommendation = (
                    f"Increase {resource} capacity by "
                    f"{planning_gap:.1f} {forecast.unit}."
                )

                reason = (
                    f"Forecast peak {peak:.1f} "
                    f"{forecast.unit} exceeds current physical "
                    f"capacity of {current_capacity:.1f} "
                    f"{forecast.unit}. "
                    f"The configured planning threshold is "
                    f"{threshold:.0f}%."
                )

                expected_impact = (
                    f"Increase total capacity to approximately "
                    f"{required_capacity:.1f} {forecast.unit} "
                    f"and restore operational headroom."
                )

            elif threshold_breached:
                recommendation = (
                    f"Plan {resource} capacity expansion of "
                    f"approximately {planning_gap:.1f} "
                    f"{forecast.unit}."
                )

                reason = (
                    f"Forecast utilization reaches "
                    f"{forecast_utilization:.1f}% against "
                    f"the configured {threshold:.0f}% "
                    f"planning threshold."
                )

                expected_impact = (
                    f"Increase capacity to approximately "
                    f"{required_capacity:.1f} {forecast.unit} "
                    f"so forecast demand operates near or below "
                    f"the configured planning threshold."
                )

            else:
                recommendation = (
                    f"Maintain current {resource} capacity."
                )

                reason = (
                    f"Forecast utilization is "
                    f"{forecast_utilization:.1f}%, below "
                    f"the configured {threshold:.0f}% "
                    f"planning threshold."
                )

                expected_impact = (
                    "Preserve current capacity headroom."
                )

            risk = (
                _severity_from_threshold(
                    forecast_utilization,
                    threshold,
                )
                if threshold_breached
                else "low"
            )

            time_horizon = (
                forecast.capacity.shortage_date.isoformat()
                if forecast.capacity.shortage_date
                else (
                    f"{len(forecast.points)} "
                    f"{forecast.frequency} periods"
                )
            )

            recommendations.append(
                RecommendationRead(
                    resource_type=resource,
                    recommendation=recommendation,
                    reason=reason,
                    supporting_metrics={
                        "current_capacity": (
                            current_capacity
                        ),
                        "current_usage": (
                            forecast.capacity.current_usage
                        ),
                        "forecast_peak": peak,
                        "current_utilization_percent": (
                            forecast.capacity.utilization_percent
                        ),
                        "forecast_utilization_percent": (
                            round(
                                forecast_utilization,
                                2,
                            )
                        ),
                        "planning_threshold_percent": (
                            threshold
                        ),
                        "recommended_capacity": (
                            round(
                                required_capacity,
                                2,
                            )
                        ),
                        "planning_expansion": (
                            round(
                                planning_gap,
                                2,
                            )
                        ),
                        "shortage_date": (
                            forecast.capacity
                            .shortage_date.isoformat()
                            if forecast.capacity.shortage_date
                            else None
                        ),
                    },
                    expected_impact=expected_impact,
                    risk=risk,
                    dependencies=dependencies[resource],
                    time_horizon=time_horizon,
                    confidence=forecast.confidence,
                    assumptions=[
                        (
                            f"Forecast model: "
                            f"{forecast.model_engine}"
                        ),
                        (
                            "Recommendation uses persisted "
                            "forecast results, current capacity, "
                            "and configured capacity thresholds."
                        ),
                        (
                            f"Configured {resource} planning "
                            f"threshold: {threshold:.0f}%."
                        ),
                    ],
                )
            )

        return recommendations


class ReportService:
    CATALOG = [
        (
            "executive",
            "Executive Capacity Report",
            (
                "Executive summary of capacity, demand, "
                "risks, and actions."
            ),
        ),
        (
            "gpu",
            "GPU Forecast Report",
            (
                "GPU demand, utilization, headroom, "
                "and forecast results."
            ),
        ),
        (
            "power",
            "Power Capacity Report",
            (
                "Power demand, capacity utilization, "
                "and shortage analysis."
            ),
        ),
        (
            "storage_network",
            "Storage & Network Report",
            (
                "Storage growth and network throughput "
                "planning."
            ),
        ),
        (
            "scenario",
            "Scenario Comparison",
            (
                "Comparison of saved expansion scenarios "
                "and assumptions."
            ),
        ),
        (
            "procurement",
            "Procurement Plan",
            (
                "Capacity-driven procurement requirements "
                "and costs."
            ),
        ),
        (
            "shortage_risk",
            "Shortage Risk Report",
            (
                "Capacity alerts, thresholds, and predicted "
                "shortages."
            ),
        ),
    ]

    @staticmethod
    def generate(
        db: Session,
        report_type: str,
        data_center_id: int | None,
        user: User,
    ) -> Report:
        from app.services.reporting import ProductionReportService

        return ProductionReportService.generate(
            db,
            report_type,
            data_center_id,
            user,
        )