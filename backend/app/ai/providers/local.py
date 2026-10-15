from __future__ import annotations

from typing import Any

from app.ai.providers.base import AIProvider


class LocalRulesProvider(AIProvider):
    name = "local"

    def generate_text(self, prompt: str, *, context: dict[str, Any]) -> str:
        # Deterministic fallback: it does not invent values and only summarizes
        # verified context supplied by the workflow.
        recommendations = context.get("recommendations") or []
        if not recommendations:
            return "Insufficient data for reliable recommendation."
        lines: list[str] = []
        for item in recommendations[:4]:
            rec = item.get("recommendation")
            reason = item.get("reason")
            if rec:
                lines.append(str(rec))
                if reason:
                    lines.append(f"Reason: {reason}")
        return " ".join(lines) if lines else "Insufficient data for reliable recommendation."

    def health_check(self) -> bool:
        return True
