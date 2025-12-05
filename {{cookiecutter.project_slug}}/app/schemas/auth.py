"""
认证数据模式定义。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """登录请求数据模式。"""
    
    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class Token(BaseModel):
    """JWT 令牌响应数据模式。"""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数


class TokenPayload(BaseModel):
    """JWT 令牌载荷数据模式。"""
    
    sub: str  # 用户ID
    exp: datetime
    iat: datetime
    type: str  # access 或 refresh
    jti: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """令牌刷新请求数据模式。"""
    
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """密码重置请求数据模式。"""
    
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """密码重置确认数据模式。"""
    
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordChange(BaseModel):
    """密码更改数据模式。"""
    
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class RegisterRequest(BaseModel):
    """用户注册数据模式。"""
    
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
