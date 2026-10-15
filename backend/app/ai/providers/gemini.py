from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.providers.base import AIProvider


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, *, context: dict[str, Any]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        grounded_prompt = (
            "You are an infrastructure planning explanation layer. Use ONLY the supplied JSON evidence. "
            "Never invent metrics, dates, costs, capacities, or conclusions not supported by evidence. "
            "If evidence is insufficient, state that clearly.\n\n"
            f"Task: {prompt}\n\nEvidence JSON:\n{json.dumps(context, default=str)}"
        )
        response = httpx.post(
            url,
            params={"key": self.api_key},
            json={"contents": [{"parts": [{"text": grounded_prompt}]}]},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()

    def health_check(self) -> bool:
        return bool(self.api_key)
