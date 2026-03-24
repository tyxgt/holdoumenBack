"""FastAPI application entrypoint.

This file is responsible for application startup, runtime environment setup,
middleware registration, and mounting all API routes.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.debug)


def configure_runtime_environment() -> None:
    # Push LangSmith-related settings into process env vars before LangChain runs.
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()


configure_runtime_environment()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Reserve startup/shutdown hooks here when the project grows.
    yield


def create_app() -> FastAPI:
    # Build the FastAPI app from centralized settings so env changes take effect
    # consistently across title, debug mode, middleware, and routing.
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Allow the frontend to call this backend across different local origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        # Keep the root route lightweight so it can be used as a smoke test.
        return {
            "message": f"{settings.app_name} is running.",
            "docs": "/docs",
        }

    # Mount all versioned business APIs under the configured prefix.
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
