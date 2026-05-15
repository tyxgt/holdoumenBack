"""认证接口的请求/响应模型。"""

import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class UserInfo(BaseModel):
    id: int
    username: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    message: str
    token: str
    user: UserInfo
    is_new_user: bool


class LogoutResponse(BaseModel):
    message: str


class MeResponse(BaseModel):
    id: int
    username: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
