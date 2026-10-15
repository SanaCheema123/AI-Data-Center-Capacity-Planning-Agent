from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.graph import build_planning_graph
from app.ai.grounding import narrative_is_grounded
from app.ai.providers import LocalRulesProvider, get_ai_provider
from app.ai.state import PlanningState
from app.ai.tools import get_alerts, get_forecasts, get_procurement, get_scenarios, get_scope_metrics
from app.models.domain import User


class AIPlanningService:
    """Grounded LangGraph orchestration over application services/database state."""

    @staticmethod
    def _initial_state(db: Session, user: User, data_center_id: int | None, question: str = "") -> PlanningState:
        return {
            "user_id": str(user.id),
            "question": question,
            "data_center_id": data_center_id,
            "metrics": get_scope_metrics(db, data_center_id),
            "forecasts": get_forecasts(db, data_center_id),
            "scenarios": get_scenarios(db, data_center_id),
            "procurement": get_procurement(db, data_center_id),
            "alerts": get_alerts(db, data_center_id),
            "evidence": [],
            "warnings": [],
        }

    @staticmethod
    def run(db: Session, user: User, data_center_id: int | None = None, question: str = "", provider_name: str | None = None) -> dict[str, Any]:
        graph = build_planning_graph()
        state = graph.invoke(AIPlanningService._initial_state(db, user, data_center_id, question))
        recommendations = state.get("recommendations") or []
        evidence = state.get("evidence") or []

        provider = get_ai_provider(provider_name)
        prompt = question.strip() or "Summarize the grounded capacity-planning recommendations."
        context = {
            "recommendations": recommendations,
            "capacity_risk": state.get("capacity_risk") or {},
            "scenario_analysis": state.get("scenario_analysis") or {},
            "procurement_analysis": state.get("procurement_analysis") or {},
            "warnings": state.get("warnings") or [],
        }
        try:
            narrative = provider.generate_text(prompt, context=context)
            if not narrative_is_grounded(narrative, evidence):
                raise ValueError("Provider response contained unsupported numeric claims")
            active_provider = provider.name
        except Exception:
            fallback = LocalRulesProvider()
            narrative = fallback.generate_text(prompt, context=context)
            active_provider = fallback.name

        state["provider"] = active_provider
        state["final_response"] = narrative
        return dict(state)

    @staticmethod
    def recommendations(db: Session, user: User, data_center_id: int | None = None, provider_name: str | None = None) -> list[dict[str, Any]]:
        state = AIPlanningService.run(db, user, data_center_id, provider_name=provider_name)
        return state.get("recommendations") or []
