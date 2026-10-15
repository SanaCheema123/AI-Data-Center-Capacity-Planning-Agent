from __future__ import annotations

from app.ai.state import PlanningState


def procurement_node(state: PlanningState) -> dict:
    items = state.get("procurement") or []
    total_cost = sum(float(x.get("estimated_cost") or 0) for x in items)
    high_priority = [x for x in items if x.get("priority") == "high"]
    analysis = {
        "item_count": len(items),
        "high_priority_count": len(high_priority),
        "estimated_total_cost": total_cost if any(x.get("estimated_cost") is not None for x in items) else None,
        "items": items,
    }
    evidence = list(state.get("evidence") or [])
    evidence.append({"node": "procurement", "source": "database.procurement_recommendations", "facts": analysis})
    return {"procurement_analysis": analysis, "evidence": evidence}
