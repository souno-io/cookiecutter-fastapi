"""
认证端点。
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import security_manager
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    Token,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    PasswordChange,
)
from app.schemas.user import UserResponse
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    description="验证用户并返回 JWT 令牌",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    OAuth2 兼容的令牌登录。
    
    获取用于后续请求的访问令牌。
    """
    # 通过邮箱查找用户
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not security_manager.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否活跃
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活",
        )
    
    # 创建令牌
    tokens = security_manager.create_token_pair(user.id)
    
    return Token(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login/json",
    response_model=Token,
    summary="用户登录 (JSON)",
    description="使用 JSON 请求体验证用户并返回 JWT 令牌",
)
async def login_json(
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    基于 JSON 的登录端点。
    
    作为 OAuth2 表单登录的替代方案。
    同时在 Cookie 中设置 token，用于服务端渲染页面的认证。
    """
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not security_manager.verify_password(
        login_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活",
        )
    
    # 为"记住我"调整令牌过期时间
    expire_minutes = (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 7
        if login_data.remember_me
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    access_token = security_manager.create_access_token(
        user.id, 
        expires_delta=timedelta(minutes=expire_minutes)
    )
    refresh_token = security_manager.create_refresh_token(user.id)
    
    # 设置 Cookie（用于服务端渲染页面的认证）
    cookie_max_age = expire_minutes * 60
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=cookie_max_age,
        httponly=True,  # 防止 XSS 攻击
        samesite="lax",  # CSRF 保护
        secure=settings.ENVIRONMENT == "production",  # 生产环境使用 HTTPS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="刷新令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    刷新访问令牌。
    
    使用刷新令牌获取新的访问令牌。
    """
    # 解码刷新令牌
    decoded = security_manager.decode_token(token_data.refresh_token)
    
    if not decoded or decoded.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )
    
    # 验证用户仍然存在且活跃
    result = await db.execute(
        select(User).where(User.id == int(decoded.user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或未激活",
        )
    
    # 创建新令牌
    tokens = security_manager.create_token_pair(user.id)
    
    # 可选：将旧的刷新令牌加入黑名单
    if decoded.jti:
        security_manager.blacklist_token(decoded.jti)
    
    return Token(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="注册新用户账户",
)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    注册新用户。
    
    使用提供的凭据创建新用户账户。
    """
    # 检查邮箱是否已存在
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )
    
    # 创建新用户
    hashed_password = security_manager.hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False,
    )
    
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    return UserResponse.model_validate(new_user)


@router.post(
    "/logout",
    summary="用户登出",
    description="登出并失效当前令牌",
)
async def logout(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    登出当前用户。
    
    在生产环境中，您可以将当前令牌加入黑名单。
    """
    # 在生产环境中，将当前令牌加入黑名单
    return {"message": "成功登出"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户",
    description="获取当前已认证用户的信息",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """获取当前用户个人资料。"""
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    summary="修改密码",
    description="修改当前用户的密码",
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    更改用户密码。
    
    需要当前密码进行验证。
    """
    # 验证当前密码
    if not security_manager.verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )
    
    # 更新密码
    current_user.hashed_password = security_manager.hash_password(
        password_data.new_password
    )
    db.add(current_user)
    
    return {"message": "密码修改成功"}
