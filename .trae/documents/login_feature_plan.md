# 登录功能实现方案

## 需求概述

为项目增加登录功能，核心特性：
- **登录即注册**：未注册用户登录时自动创建账号
- **用户名+密码**：使用用户名作为登录标识
- **Token存储在Cookie**：自动携带，支持HttpOnly安全属性
- **密码严格规则**：至少8位，必须包含大小写字母、数字和特殊字符
- **Token有效期**：7天

## 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 密码加密 | passlib[bcrypt] | 行业标准的密码哈希库 |
| JWT | python-jose[cryptography] | FastAPI官方推荐的JWT库 |
| 数据库 | PostgreSQL + SQLAlchemy 2.0 | 已在项目中配置 |

## 文件结构

```
app/
├── core/
│   ├── config.py          # [修改] 添加JWT配置
│   ├── security.py        # [新建] 密码哈希和JWT工具
│   └── deps.py            # [新建] 认证依赖注入
├── db/
│   └── session.py         # [新建] 数据库连接管理
├── models/
│   ├── __init__.py        # [新建] 模型导出
│   └── user.py            # [新建] 用户模型
├── schemas/
│   └── auth.py            # [新建] 认证相关的Pydantic模型
├── api/
│   └── routes/
│       └── auth.py        # [新建] 认证路由
└── main.py                # [修改] 添加数据库生命周期
```

## 详细实现步骤

### 步骤 1：添加依赖

编辑 `pyproject.toml`，添加以下依赖：

```toml
"passlib[bcrypt]>=1.7.4,<2.0.0",
"python-jose[cryptography]>=3.3.0,<4.0.0",
```

### 步骤 2：更新配置文件

修改 `app/core/config.py`，添加JWT相关配置：

```python
# JWT 配置
jwt_secret_key: str | None = None
jwt_algorithm: str = "HS256"
jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7天
```

### 步骤 3：创建数据库连接

创建 `app/db/session.py`：

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.resolved_database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
```

### 步骤 4：创建用户模型

创建 `app/models/user.py`：

```python
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 步骤 5：创建安全工具模块

创建 `app/core/security.py`：

```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
```

### 步骤 6：创建认证依赖

创建 `app/core/deps.py`：

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception
    return user
```

### 步骤 7：创建认证Schema

创建 `app/schemas/auth.py`：

```python
from pydantic import BaseModel, field_validator
import re

class LoginRequest(BaseModel):
    username: str
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少8位")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含小写字母")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("密码必须包含特殊字符")
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: str
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    is_new_user: bool
```

### 步骤 8：创建认证路由

创建 `app/api/routes/auth.py`：

```python
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()
    
    is_new_user = False
    
    if not user:
        user = User(
            username=request.username,
            hashed_password=get_password_hash(request.password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    else:
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="密码错误",
            )
    
    access_token = create_access_token(data={"sub": user.username})
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    
    return LoginResponse(
        message="注册成功" if is_new_user else "登录成功",
        user=UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat(),
        ),
        is_new_user=is_new_user,
    )

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "已退出登录"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at.isoformat(),
    )
```

### 步骤 9：更新路由注册

修改 `app/api/router.py`：

```python
from app.api.routes.auth import router as auth_router
# ...
api_router.include_router(auth_router)
```

### 步骤 10：更新应用生命周期

修改 `app/main.py`，添加数据库初始化：

```python
from app.db.session import Base, engine

@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
```

## API 接口文档

### POST /api/v1/auth/login

**描述**：登录接口，未注册用户自动注册

**请求体**：
```json
{
    "username": "string",
    "password": "string"
}
```

**密码规则**：
- 至少8位字符
- 必须包含小写字母
- 必须包含大写字母
- 必须包含数字
- 必须包含特殊字符 (!@#$%^&*(),.?":{}|<>)

**响应**：
```json
{
    "message": "登录成功" | "注册成功",
    "user": {
        "id": 1,
        "username": "string",
        "created_at": "2024-01-01T00:00:00"
    },
    "is_new_user": false
}
```

**Cookie**：
- 名称：`access_token`
- 属性：HttpOnly, Secure, SameSite=Lax
- 有效期：7天

### POST /api/v1/auth/logout

**描述**：退出登录，清除Cookie

### GET /api/v1/auth/me

**描述**：获取当前登录用户信息

**响应**：
```json
{
    "id": 1,
    "username": "string",
    "created_at": "2024-01-01T00:00:00"
}
```

## Railway 部署配置

### 环境变量配置

在 Railway 项目中设置以下环境变量：

```env
# 数据库连接（Railway PostgreSQL 插件自动提供）
DATABASE_URL=${{Postgres.DATABASE_URL}}

# JWT 密钥（必须手动设置，建议使用强随机字符串）
JWT_SECRET_KEY=your-super-secret-key-at-least-32-characters-long

# 其他可选配置
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### 生成 JWT 密钥

```bash
# 使用 openssl 生成随机密钥
openssl rand -hex 32
```

### Railway PostgreSQL 插件

1. 在 Railway 项目中添加 PostgreSQL 插件
2. Railway 会自动设置 `DATABASE_URL` 环境变量
3. 应用启动时会自动创建 `users` 表

## 验证步骤

1. 安装依赖：`pip install -e .`
2. 配置 `.env` 文件
3. 启动服务：`uvicorn app.main:app --reload`
4. 访问 `/docs` 测试接口
5. 测试登录流程：
   - 使用新用户名登录 → 自动注册
   - 再次登录 → 正常登录
   - 访问 `/api/v1/auth/me` → 获取用户信息

## 前端对接说明

### 登录流程

1. 调用 `POST /api/v1/auth/login`
2. 成功后 Cookie 自动设置，后续请求自动携带
3. 根据 `is_new_user` 判断是新用户还是老用户
4. 显示相应提示信息

### 受保护接口

对于需要登录的接口，前端无需额外处理，Cookie 会自动携带。如果未登录，后端返回 401 错误。

### 退出登录

调用 `POST /api/v1/auth/logout` 清除 Cookie
