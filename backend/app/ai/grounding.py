from __future__ import annotations

import json
import re
from typing import Any

_NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?")


def _flatten_numbers(value: Any) -> list[float]:
    out: list[float] = []
    if isinstance(value, bool) or value is None:
        return out
    if isinstance(value, (int, float)):
        out.append(float(value))
    elif isinstance(value, dict):
        for child in value.values():
            out.extend(_flatten_numbers(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            out.extend(_flatten_numbers(child))
    return out


def narrative_is_grounded(text: str, evidence: list[dict[str, Any]]) -> bool:
    """Reject provider text containing numeric claims absent from workflow evidence.

    This is intentionally conservative. Structured recommendations remain the
    authoritative AI output; provider prose is an optional explanation layer.
    """
    allowed = _flatten_numbers(evidence)
    if not allowed:
        return not bool(_NUMBER_RE.search(text))
    for token in _NUMBER_RE.findall(text):
        number = float(token)
        if not any(abs(number - candidate) <= max(0.02, abs(candidate) * 0.001) for candidate in allowed):
            return False
    return True
