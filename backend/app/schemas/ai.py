from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    data_center_id: int | None = None
    provider: Literal["local", "gemini", "groq"] | None = None


class AIWorkflowRequest(BaseModel):
    data_center_id: int | None = None
    provider: Literal["local", "gemini", "groq"] | None = None


class AIWorkflowResponse(BaseModel):
    provider: str
    grounded: bool = True
    final_response: str
    analysis: dict[str, Any]
    forecast_analysis: dict[str, Any]
    capacity_risk: dict[str, Any]
    scenario_analysis: dict[str, Any]
    procurement_analysis: dict[str, Any]
    recommendations: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    warnings: list[str]


class AIProviderStatus(BaseModel):
    configured_provider: str
    active_provider: str
    available: bool
    grounded: bool = True
    providers: dict[str, bool]
