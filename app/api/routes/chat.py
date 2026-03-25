"""Chat API endpoints.

This module exposes the HTTP route that receives user messages and forwards them
to the LangChain service layer.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

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
) -> ChatResponse | StreamingResponse:
    try:
        if payload.stream:
            async def event_stream():
                meta = {
                    "model": settings.resolved_model,
                    "provider": settings.normalized_provider,
                }
                yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"

                try:
                    async for chunk in service.stream_chat(
                        user_message=payload.message,
                        system_prompt=payload.system_prompt,
                    ):
                        yield (
                            "event: delta\ndata: "
                            f"{json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
                        )
                except Exception as exc:
                    yield (
                        "event: error\ndata: "
                        f"{json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"
                    )
                    return

                yield "event: done\ndata: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

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
