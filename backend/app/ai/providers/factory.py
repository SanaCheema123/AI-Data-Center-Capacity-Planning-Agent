from __future__ import annotations

from app.ai.providers.base import AIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.local import LocalRulesProvider
from app.core.config import settings


def get_ai_provider(name: str | None = None) -> AIProvider:
    requested = (name or settings.ai_provider or "local").strip().lower()
    if requested == "gemini" and settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key)
    if requested == "groq" and settings.groq_api_key:
        return GroqProvider(settings.groq_api_key)
    return LocalRulesProvider()
