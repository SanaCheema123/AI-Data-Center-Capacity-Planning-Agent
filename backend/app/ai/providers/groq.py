from __future__ import annotations

import json
from typing import Any

import httpx

from app.ai.providers.base import AIProvider


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, *, context: dict[str, Any]) -> str:
        grounded_prompt = (
            "Use only the supplied infrastructure evidence. Do not invent any metric, date, cost, capacity, "
            "forecast, or recommendation premise. Say when evidence is insufficient.\n\n"
            f"Task: {prompt}\n\nEvidence JSON:\n{json.dumps(context, default=str)}"
        )
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": "You are a grounded data-center capacity planning explainer."},
                    {"role": "user", "content": grounded_prompt},
                ],
            },
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def health_check(self) -> bool:
        return bool(self.api_key)
