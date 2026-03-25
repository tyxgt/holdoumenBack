"""Centralized application settings.

This file loads values from `.env`, normalizes provider-specific configuration,
and exposes a cached settings object for the rest of the project.
"""
# 中央应用设置模块
# 负责加载环境变量、归一化供应商特定配置并缓存设置对象。
# 该模块在应用启动时加载一次，后续请求从缓存中获取设置对象。

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

class Settings(BaseSettings):
    """All runtime configuration for the backend."""

    app_name: str = "FastAPI LangChain Backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_timeout: float = 60.0
    llm_max_retries: int = 2
    ark_api_key: str | None = None
    ark_base_url: str | None = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str | None = None

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str | None = "fastapi-langchain-backend"
    langsmith_endpoint: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        # Support comma-separated origins in `.env` while still accepting lists.
        if isinstance(value, list):
            return value
        if not value:
            return ["*"]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def normalized_provider(self) -> str:
        # Normalize provider names once so downstream code only handles one form.
        return self.llm_provider.strip().lower()

    @property
    def resolved_api_key(self) -> str | None:
        # Resolve the active API key based on the selected LLM provider.
        if self.normalized_provider == "ark":
            return self.ark_api_key or self.openai_api_key
        return self.openai_api_key

    @property
    def resolved_base_url(self) -> str | None:
        # Ark uses an OpenAI-compatible endpoint, so the service can share one path.
        if self.normalized_provider == "ark":
            return self.ark_base_url or self.openai_base_url
        return self.openai_base_url

    @property
    def resolved_model(self) -> str:
        # Expose the final model that the service should really call.
        if self.normalized_provider == "ark":
            return self.ark_model or self.llm_model
        return self.llm_model


@lru_cache
def get_settings() -> Settings:
    # 获取应用配置
    return Settings()
