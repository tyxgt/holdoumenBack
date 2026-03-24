"""Health check endpoints."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    # Expose only lightweight runtime state so operators can quickly verify
    # whether the service is up and whether LLM credentials are configured.
    return {
        "status": "ok",
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "llm_configured": bool(settings.resolved_api_key),
    }
