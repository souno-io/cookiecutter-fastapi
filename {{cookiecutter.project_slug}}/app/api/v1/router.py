"""
API v1 路由聚合。

将所有端点路由合并为单个路由。
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, health, roles, files

api_router = APIRouter()

# 健康检查端点（无前缀）
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

# 认证端点
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# 用户管理端点
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# 角色管理端点
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["Roles"],
)

# 文件管理端点
api_router.include_router(
    files.router,
    prefix="/files",
    tags=["Files"],
)
