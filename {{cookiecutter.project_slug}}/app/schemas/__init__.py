"""Pydantic 数据模式模块导出。"""

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
)
from app.schemas.auth import (
    Token,
    TokenPayload,
    LoginRequest,
    RefreshTokenRequest,
)
from app.schemas.common import (
    PaginatedResponse,
    MessageResponse,
    HealthResponse,
)
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
)

__all__ = [
    # 用户相关
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # 认证相关
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RefreshTokenRequest",
    # 通用模式
    "PaginatedResponse",
    "MessageResponse",
    "HealthResponse",
    # 角色相关
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
]
