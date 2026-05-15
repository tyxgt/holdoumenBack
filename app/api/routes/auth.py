"""认证接口路由。"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """从请求中解析当前用户（依赖项）。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload["sub"]
    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """用户登录。如用户不存在则自动注册。"""
    result = await session.execute(
        select(User).where(User.username == payload.username)
    )
    user = result.scalar_one_or_none()

    is_new_user = False
    if user is None:
        user = User(
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        is_new_user = True
    else:
        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="密码错误",
            )

    token = create_access_token({"sub": str(user.id)})
    return LoginResponse(
        message="登录成功" if not is_new_user else "注册成功",
        token=token,
        user=user,
        is_new_user=is_new_user,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout() -> LogoutResponse:
    """退出登录（客户端需自行删除 token）。"""
    return LogoutResponse(message="已退出登录")


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    """获取当前登录用户信息。"""
    return MeResponse.model_validate(current_user)
