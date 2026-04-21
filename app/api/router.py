"""API 总路由入口。

可以把它理解成前端项目里的“总路由配置文件”：
把各个业务模块的子路由汇总后，再统一挂到应用上。
"""

from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router

# `APIRouter` 是 FastAPI 的子路由容器，作用类似“可组合的路由模块”。
api_router = APIRouter()

# 这里把健康检查和聊天接口合并到总路由里。
# 后面如果新增用户、订单、文件上传等模块，也是在这里继续 include。
api_router.include_router(health_router)
api_router.include_router(chat_router)
