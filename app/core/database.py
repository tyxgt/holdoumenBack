"""异步数据库引擎和会话管理。

未配置 DATABASE_URL 时自动使用本地 SQLite 文件（dev.db），方便开发。
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
database_url = _settings.resolved_database_url

if database_url:
    _engine = create_async_engine(
        database_url,
        echo=_settings.database_echo,
        pool_size=_settings.database_pool_size,
        max_overflow=_settings.database_max_overflow,
    )
else:
    db_path = Path(os.path.dirname(os.path.dirname(__file__))) / "dev.db"
    _engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=_settings.database_echo,
    )

_async_session_maker = async_sessionmaker(
    _engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖项。"""
    async with _async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """创建所有表（生产环境应使用 Alembic 迁移）。"""
    from app.models.user import User  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
