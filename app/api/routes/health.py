"""健康检查接口。

这类接口通常给前端、测试脚本、运维探针使用，用来快速确认：
- 服务是否活着
- 当前环境是什么
- LLM 关键配置是否已经就绪
"""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    # 这里只返回轻量级信息，不做真正的模型调用。
    # 好处是健康检查足够快，也不会平白消耗 LLM 配额。
    return {
        "status": "ok",
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "llm_configured": bool(settings.resolved_api_key),
    }
