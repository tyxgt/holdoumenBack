"""Chat API endpoints.

This module exposes the HTTP route that receives user messages and forwards them
to the LangChain service layer.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.langchain_service import (
    LangChainConfigurationError,
    LangChainService,
    get_langchain_service,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: LangChainService = Depends(get_langchain_service),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    try:
        # Delegate LLM invocation to the service layer so provider logic stays
        # outside the route handler.
        content = await service.chat(
            user_message=payload.message,
            system_prompt=payload.system_prompt,
        )
    except LangChainConfigurationError as exc:
        # Configuration errors usually mean `.env` is incomplete or inconsistent.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Convert upstream LLM failures into a stable API response for callers.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM invocation failed.",
        ) from exc

    return ChatResponse(
        answer=content,
        model=settings.resolved_model,
        provider=settings.normalized_provider,
    )
