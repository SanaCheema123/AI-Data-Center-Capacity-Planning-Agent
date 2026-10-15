from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.providers import get_ai_provider
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.domain import User
from app.schemas.ai import AIChatRequest, AIProviderStatus, AIWorkflowRequest, AIWorkflowResponse
from app.schemas.planning import RecommendationRead
from app.services.ai_planning import AIPlanningService

router = APIRouter()


@router.get("/status", response_model=AIProviderStatus)
def status(_: User = Depends(get_current_user)) -> AIProviderStatus:
    provider = get_ai_provider()
    return AIProviderStatus(
        configured_provider=settings.ai_provider,
        active_provider=provider.name,
        available=provider.health_check(),
        grounded=True,
        providers={
            "local": True,
            "gemini": bool(settings.gemini_api_key),
            "groq": bool(settings.groq_api_key),
        },
    )


@router.get("/recommendations", response_model=list[RecommendationRead])
def recommendations(
    data_center_id: int | None = Query(default=None),
    provider: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return AIPlanningService.recommendations(db, user, data_center_id, provider)


@router.post("/workflow", response_model=AIWorkflowResponse)
def workflow(
    payload: AIWorkflowRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIWorkflowResponse:
    state = AIPlanningService.run(db, user, payload.data_center_id, provider_name=payload.provider)
    return AIWorkflowResponse(
        provider=state.get("provider", "local"),
        final_response=state.get("final_response", ""),
        analysis=state.get("analysis") or {},
        forecast_analysis=state.get("forecast_analysis") or {},
        capacity_risk=state.get("capacity_risk") or {},
        scenario_analysis=state.get("scenario_analysis") or {},
        procurement_analysis=state.get("procurement_analysis") or {},
        recommendations=state.get("recommendations") or [],
        evidence=state.get("evidence") or [],
        warnings=state.get("warnings") or [],
    )


@router.post("/chat", response_model=AIWorkflowResponse)
def chat(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AIWorkflowResponse:
    state = AIPlanningService.run(
        db,
        user,
        payload.data_center_id,
        question=payload.question,
        provider_name=payload.provider,
    )
    return AIWorkflowResponse(
        provider=state.get("provider", "local"),
        final_response=state.get("final_response", ""),
        analysis=state.get("analysis") or {},
        forecast_analysis=state.get("forecast_analysis") or {},
        capacity_risk=state.get("capacity_risk") or {},
        scenario_analysis=state.get("scenario_analysis") or {},
        procurement_analysis=state.get("procurement_analysis") or {},
        recommendations=state.get("recommendations") or [],
        evidence=state.get("evidence") or [],
        warnings=state.get("warnings") or [],
    )
