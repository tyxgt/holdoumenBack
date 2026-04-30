"""全局配置模块。

这个文件专门负责：
- 从 `.env` 读取配置
- 做一些格式清洗和兼容处理
- 对外提供“当前真正生效的配置”

如果你是前端，可以把这里理解成“后端版的配置中心”。
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """后端运行时配置对象。

    `BaseSettings` 是 Pydantic 提供的能力，作用类似：
    - 定义一份“带类型”的配置 schema
    - 再自动从环境变量 / `.env` 文件里填充值
    """

    # 基础服务配置
    app_name: str = "FastAPI LangChain Backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"

    # `cors_origins` 想要的最终类型是 `list[str]`。
    # 但 `.env` 里通常会写成逗号分隔字符串，所以这里配合下面的 validator 做转换。
    # `NoDecode` 的作用是告诉 pydantic-settings：不要尝试把它当 JSON 自动解析。
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True

    # LLM 通用配置
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_timeout: float = 60.0
    llm_max_retries: int = 2

    # Ark 专属配置。因为 Ark 兼容 OpenAI 接口，所以最终仍会走同一套客户端。
    ark_api_key: str | None = None
    ark_base_url: str | None = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str | None = None

    # LangSmith 调试/追踪配置
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str | None = "fastapi-langchain-backend"
    langsmith_endpoint: str | None = None

    # 数据库配置
    # 真实连接信息只应放在 `.env` 或部署平台环境变量中，不要提交到仓库。
    # PostgreSQL 推荐优先使用 DATABASE_URL；如果部署平台仅提供拆分字段，
    # 可使用 PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE。
    database_url: str | None = None
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    pghost: str | None = None
    pgport: int = 5432
    pguser: str | None = None
    pgpassword: str | None = None
    pgdatabase: str | None = None

    # JWT 配置
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7

    # 告诉 Pydantic 去哪里找环境变量。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        """兼容 `.env` 里的逗号分隔写法。

        例如：
        `CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`
        会被转换成：
        `["http://localhost:3000", "http://127.0.0.1:3000"]`
        """
        if isinstance(value, list):
            return value
        if not value:
            return ["*"]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def normalized_provider(self) -> str:
        # 把供应商名统一转成小写，避免后续代码反复处理大小写差异。
        # 比如 `OpenAI`、`OPENAI`、`openai` 最终都按 `openai` 处理。
        return self.llm_provider.strip().lower()

    @property
    def resolved_api_key(self) -> str | None:
        # 根据当前选中的 provider，计算“本次请求真正应该使用的 key”。
        # 这样业务层不需要再关心 openai / ark 的分支细节。
        if self.normalized_provider == "ark":
            return self.ark_api_key or self.openai_api_key
        return self.openai_api_key

    @property
    def resolved_base_url(self) -> str | None:
        # Ark 走的是 OpenAI 兼容接口，所以这里也统一产出最终 base_url。
        if self.normalized_provider == "ark":
            return self.ark_base_url or self.openai_base_url
        return self.openai_base_url

    @property
    def resolved_model(self) -> str:
        # 暴露“最终实际调用的模型名”。
        # 对外层代码来说，只拿这个值就够了，不用自己判断 provider 分支。
        if self.normalized_provider == "ark":
            return self.ark_model or self.llm_model
        return self.llm_model

    @property
    def resolved_database_url(self) -> str | None:
        """返回最终生效的数据库连接串。

        优先使用标准的 `DATABASE_URL`；如果只配置了 PostgreSQL 拆分变量，
        则动态拼装 SQLAlchemy 异步连接串，避免在代码或模板中暴露真实密码。
        """
        if self.database_url:
            return self.database_url
        if not all([self.pghost, self.pguser, self.pgpassword, self.pgdatabase]):
            return None
        return (
            f"postgresql+asyncpg://{self.pguser}:{self.pgpassword}"
            f"@{self.pghost}:{self.pgport}/{self.pgdatabase}"
        )


@lru_cache
def get_settings() -> Settings:
    # `lru_cache` 让这个函数在进程内只创建一次 Settings。
    # 效果类似“单例配置对象”，避免每次请求都重复解析 `.env`。
    return Settings()
