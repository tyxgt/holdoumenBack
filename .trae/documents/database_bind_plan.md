# 数据库绑定方案（使用扣子编程云数据库）

## 项目现状分析

当前项目是一个 **FastAPI + LangChain** 后端服务，核心特征：
- 使用 `pydantic-settings` 管理配置
- 从 `.env` 文件读取环境变量
- 目前无任何数据库相关代码

## 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 数据库 | 扣子编程云数据库 | 无需本地安装，直接使用云服务 |
| ORM | SQLAlchemy 2.0 | Python 最成熟的 ORM，支持异步操作 |
| 驱动 | 根据数据库类型自动适配 | 由扣子编程提供的连接信息决定 |

## 实现步骤

### 步骤 1：添加数据库依赖

编辑 `pyproject.toml`，添加以下依赖：

```toml
[project]
dependencies = [
    # ... 现有依赖 ...
    "sqlalchemy>=2.0,<3.0",
    "asyncpg>=0.29,<0.30",      # PostgreSQL 异步驱动
    "aiosqlite>=0.20,<0.21",    # SQLite 异步驱动（可选，用于测试）
    "alembic>=1.12,<2.0",       # 数据库迁移工具（可选）
]
```

### 步骤 2：配置数据库连接信息

获取扣子编程提供的数据库连接信息，通常包括：
- **数据库类型**（MySQL、PostgreSQL 等）
- **主机地址**（如：`db.example.com`）
- **端口**（如：`5432`）
- **数据库名称**
- **用户名**
- **密码**

在 `app/core/config.py` 中添加数据库配置：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 数据库配置（使用扣子编程云数据库）
    database_url: str = "postgresql+asyncpg://username:password@host:port/database_name"
    database_echo: bool = False  # 是否打印 SQL 日志
    database_pool_size: int = 5
    database_max_overflow: int = 10
```

在 `.env` 文件中配置实际的数据库连接信息：

```env
# 数据库配置（替换为扣子编程提供的信息）
DATABASE_URL=postgresql+asyncpg://your_username:your_password@your_host:your_port/your_database
DATABASE_ECHO=false
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
```

### 步骤 3：创建数据库连接工厂

创建 `app/core/database.py`：

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 创建异步引擎（自动适配连接字符串中的数据库类型）
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

# 创建异步会话工厂
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有数据库模型的基类"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖函数，用于获取数据库会话"""
    async with async_session_maker() as session:
        yield session
```

### 步骤 4：创建数据模型

创建 `app/models/` 目录和示例模型文件，例如 `app/models/user.py`：

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 步骤 5：创建数据库初始化逻辑

修改 `app/main.py`，在生命周期钩子中添加数据库表创建：

```python
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI 生命周期钩子"""
    # 启动时创建所有表（如果表不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时清理资源
    await engine.dispose()
```

### 步骤 6：创建 Pydantic Schema

创建 `app/schemas/user.py`：

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### 步骤 7：创建 CRUD 操作

创建 `app/crud/user.py`：

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    user = User(**user_in.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
```

### 步骤 8：创建 API 路由

创建 `app/api/routes/user.py`：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.user import create_user, get_user_by_email
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
async def create_user_endpoint(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, user_in)
```

### 步骤 9：注册路由

修改 `app/api/router.py`，注册用户路由：

```python
from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.user import router as user_router  # 新增

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(user_router)  # 新增
```

## 配置说明

### 数据库连接字符串格式

根据扣子编程提供的数据库类型，使用对应的连接字符串格式：

```bash
# PostgreSQL
postgresql+asyncpg://username:password@host:port/database_name

# MySQL（需要安装 aiomysql）
mysql+aiomysql://username:password@host:port/database_name

# SQLite（用于测试环境）
sqlite+aiosqlite:///./test.db
```

### 环境变量配置

在 `.env` 文件中配置实际的数据库连接信息：

```env
# 请替换为扣子编程提供的数据库连接信息
DATABASE_URL=postgresql+asyncpg://your_username:your_password@your_host:your_port/your_database
```

## 验证步骤

1. **安装依赖**：
   ```bash
   pip install -e .
   ```

2. **设置环境变量**：
   - 复制 `.env.example` 为 `.env`
   - 在 `.env` 中配置扣子编程提供的数据库连接信息

3. **启动服务**：
   ```bash
   uvicorn app.main:app --reload
   ```

4. **测试接口**：
   - 访问 `http://localhost:8000/docs`
   - 使用 `/api/v1/users/` 接口创建用户
   - 验证数据是否正确写入数据库

## 总结

通过以上步骤，项目将具备完整的数据库绑定能力：

1. ✅ 异步数据库连接池
2. ✅ SQLAlchemy 2.0 ORM 支持
3. ✅ 使用扣子编程云数据库（无需本地设置）
4. ✅ 数据库配置通过环境变量管理
5. ✅ FastAPI 依赖注入集成

**关键步骤**：获取扣子编程提供的数据库连接信息（`DATABASE_URL`），并配置到 `.env` 文件中即可开始使用。