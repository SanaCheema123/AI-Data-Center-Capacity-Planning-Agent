from __future__ import annotations

from typing import Any, Callable

from app.ai.nodes import (
    capacity_risk_node,
    data_analysis_node,
    forecast_analysis_node,
    procurement_node,
    recommendation_node,
    scenario_analysis_node,
)
from app.ai.state import PlanningState

_NODE_SEQUENCE: list[Callable[[PlanningState], dict]] = [
    data_analysis_node,
    forecast_analysis_node,
    capacity_risk_node,
    scenario_analysis_node,
    procurement_node,
    recommendation_node,
]


class SequentialPlanningGraph:
    """Development fallback used only when the optional LangGraph package is absent.

    Production installs LangGraph from pyproject.toml and therefore uses the
    StateGraph implementation below. Keeping this fallback makes local/offline
    development and deterministic unit testing possible without changing the
    workflow's node contracts.
    """

    engine = "sequential-fallback"

    def invoke(self, initial_state: PlanningState) -> PlanningState:
        state: PlanningState = dict(initial_state)
        for node in _NODE_SEQUENCE:
            state.update(node(state))
        return state


def build_planning_graph() -> Any:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return SequentialPlanningGraph()

    graph = StateGraph(PlanningState)
    graph.add_node("data_analysis", data_analysis_node)
    graph.add_node("forecast_analysis", forecast_analysis_node)
    graph.add_node("capacity_risk", capacity_risk_node)
    graph.add_node("scenario_analysis", scenario_analysis_node)
    graph.add_node("procurement", procurement_node)
    graph.add_node("recommendations", recommendation_node)

    graph.add_edge(START, "data_analysis")
    graph.add_edge("data_analysis", "forecast_analysis")
    graph.add_edge("forecast_analysis", "capacity_risk")
    graph.add_edge("capacity_risk", "scenario_analysis")
    graph.add_edge("scenario_analysis", "procurement")
    graph.add_edge("procurement", "recommendations")
    graph.add_edge("recommendations", END)
    compiled = graph.compile()
    try:
        compiled.engine = "langgraph"
    except Exception:
        pass
    return compiled
