"""Top-level API router composition.

This file gathers all route modules into one router so `app.main` only needs to
include a single object.
"""

from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
# Register each business route module in one place for easier expansion later.
api_router.include_router(health_router)
api_router.include_router(chat_router)
