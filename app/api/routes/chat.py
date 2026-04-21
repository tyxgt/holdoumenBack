"""聊天接口路由。

这个文件只做两件事：
- 接收 HTTP 请求
- 把请求转交给 service 层处理

它本身不关心模型怎么接，也不关心 LangChain 内部细节。
这样路由层会比较薄，职责更清晰。
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

# 最终路径前缀会和 `app/main.py` 里的 `api_prefix` 叠加。
# 所以这个接口真正地址是 `/api/v1/chat`。
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: LangChainService = Depends(get_langchain_service),
    settings: Settings = Depends(get_settings),
) -> ChatResponse | StreamingResponse:
    """聊天接口。

    参数说明：
    - `payload`：请求体，FastAPI 会自动按 `ChatRequest` 校验 JSON
    - `service`：通过依赖注入拿到 LangChainService 实例
    - `settings`：通过依赖注入拿到当前配置

    如果你熟悉前端，可以把 `Depends(...)` 理解成：
    “这个函数需要这些依赖，框架会在调用前帮你准备好”。
    """
    try:
        if payload.stream:
            # 当 `stream=true` 时，不一次性返回完整答案，而是走 SSE 流式输出。
            # 前端可以用 `EventSource` 或基于 fetch stream 的方式逐段消费。
            async def event_stream():
                # 第一条事件先告诉前端：这次请求用了哪个 provider / model。
                meta = {
                    "model": settings.resolved_model,
                    "provider": settings.normalized_provider,
                }
                yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"

                try:
                    # `service.stream_chat()` 会不断产出模型增量文本。
                    async for chunk in service.stream_chat(
                        user_message=payload.message,
                        system_prompt=payload.system_prompt,
                    ):
                        # 每一小段文本都包装成一条 SSE `delta` 事件发给前端。
                        yield (
                            "event: delta\ndata: "
                            f"{json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
                        )
                except Exception as exc:
                    # 流式场景下没法像普通 JSON 那样直接抛 HTTPException，
                    # 所以要把错误也编码成 SSE 事件返回给前端。
                    yield (
                        "event: error\ndata: "
                        f"{json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"
                    )
                    return

                # 明确告诉前端流已经结束，方便前端关闭 loading 状态。
                yield "event: done\ndata: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    # 这些 header 都是在尽量保证 SSE 可以持续、实时地往前端推数据。
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # 非流式场景就比较直接：等待 service 返回完整文本，再组装成 JSON 响应。
        content = await service.chat(
            user_message=payload.message,
            system_prompt=payload.system_prompt,
        )
    except LangChainConfigurationError as exc:
        # 配置错误一般意味着 `.env` 没配好，比如 key 缺失、provider 写错。
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # 这里兜底处理模型调用失败，避免把底层 SDK 的异常细节直接暴露给前端。
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM invocation failed.",
        ) from exc

    # 最终响应结构由 `ChatResponse` 约束，保证前后端字段稳定。
    return ChatResponse(
        answer=content,
        model=settings.resolved_model,
        provider=settings.normalized_provider,
    )
