"""
API 依赖注入。

提供可重用的依赖项：
- 数据库会话
- 当前用户认证
- 权限检查
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import security_manager, TokenData
from app.db.session import get_db
from app.models.user import User


# 用于令牌提取的 OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """
    从 JWT 令牌获取当前已认证的用户。
    
    参数：
        db: 数据库会话
        token: 来自 Authorization 头的 JWT 令牌
        
    返回：
        当前用户实例
        
    异常：
        HTTPException: 如果认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    # 解码令牌
    token_data: Optional[TokenData] = security_manager.decode_token(token)
    
    if not token_data:
        raise credentials_exception
    
    if token_data.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从数据库获取用户
    result = await db.execute(
        select(User).where(User.id == int(token_data.user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户。
    
    参数：
        current_user: 当前已认证的用户
        
    返回：
        活跃用户实例
        
    异常：
        HTTPException: 如果用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    获取当前超级用户。
    
    参数：
        current_user: 当前活跃用户
        
    返回：
        超级用户实例
        
    异常：
        HTTPException: 如果用户不是超级用户
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    return current_user


async def get_optional_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """
    如果已认证则获取当前用户，否则返回 None。
    
    适用于同时支持已认证和匿名用户的端点。
    
    参数：
        db: 数据库会话
        token: 可选的 JWT 令牌
        
    返回：
        用户实例或 None
    """
    if not token:
        return None
    
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


class RoleChecker:
    """
    用于检查用户角色的依赖类。
    
    用法：
        @router.get("/admin")
        async def admin_only(
            _: bool = Depends(RoleChecker(["admin", "super_admin"])),
            current_user: User = Depends(get_current_active_user)
        ):
            ...
    """
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self, 
        current_user: User = Depends(get_current_active_user),
    ) -> bool:
        if current_user.is_superuser:
            return True
        
        if not current_user.has_any_role(self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="角色权限不足",
            )
        return True
