"""FastAPI 应用入口。

前端可以把这个文件理解成后端项目的“启动文件”：
- 先读取全局配置
- 再初始化日志和运行时环境
- 最后创建 FastAPI 实例并挂载所有路由
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

# `get_settings()` 会从 `.env` 里读取配置，并且借助缓存保证全项目复用同一份设置。
settings = get_settings()
# 启动阶段先把日志配置好，后续其他模块打印日志时都会走这里的规则。
configure_logging(settings.debug)


def configure_runtime_environment() -> None:
    """把 LangChain 运行时依赖的环境变量写入 `os.environ`。

    如果你熟悉前端，可以把它理解成在应用真正启动前，先把一部分
    `process.env` 风格的运行参数准备好，供底层 SDK 读取。
    """

    # LangSmith 是 LangChain 官方的链路追踪/调试平台。
    # 这里不是业务逻辑，只是在启动时把追踪配置注入运行环境。
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    # 布尔值要转成小写字符串，底层通常读取的是 `"true"` / `"false"`。
    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()


configure_runtime_environment()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI 生命周期钩子。

    可以把它理解成应用级的 `onMounted / onUnmounted`：
    - `yield` 前面的代码会在服务启动时执行
    - `yield` 后面的代码会在服务关闭时执行

    当前项目还没有额外的启动/销毁逻辑，所以这里只保留空骨架。
    """
    yield


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""

    # 用统一配置来创建应用，避免标题、debug、路由前缀等配置散落在各处。
    # 这种“工厂函数”写法也方便测试时单独创建 app。
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS 中间件负责解决浏览器跨域问题。
    # 对前端来说，最常见的场景就是本地 `localhost:3000` 调这个后端接口。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        # 根路由通常用来做最轻量的存活检查，确认服务有没有成功启动。
        return {
            "message": f"{settings.app_name} is running.",
            "docs": "/docs",
        }

    # 统一挂载业务路由。
    # 最终接口会长成 `/api/v1/chat`、`/api/v1/health` 这样的形式。
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


# uvicorn 启动时默认会寻找这个名为 `app` 的 FastAPI 实例。
app = create_app()
