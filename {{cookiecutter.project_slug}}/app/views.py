"""
视图路由模块。

提供 Web 页面路由和权限控制。
"""
{%- if cookiecutter.include_jinja2 == "yes" %}

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import security_manager
from app.db.session import get_db
from app.models.user import User


router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    从 Cookie 或 Authorization 头中获取当前用户。
    
    这是一个可选依赖，不会在未登录时抛出异常。
    """
    token = None
    
    # 尝试从 Cookie 获取 token
    token = request.cookies.get("access_token")
    
    # 尝试从 Authorization 头获取 token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        return None
    
    # 解码 token
    token_data = security_manager.decode_token(token)
    if not token_data or token_data.token_type != "access":
        return None
    
    # 获取用户
    result = await db.execute(
        select(User).where(User.id == int(token_data.user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        return None
    
    return user


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    要求用户已登录的依赖。
    
    如果未登录，重定向到登录页面。
    """
    user = await get_current_user_from_cookie(request, db)
    
    if not user:
        # 保存当前页面作为登录后的重定向目标
        redirect_url = f"/login?redirect={request.url.path}"
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": redirect_url},
        )
    
    return user


async def require_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    要求用户是管理员的依赖。
    
    如果不是管理员，返回 403 错误。
    """
    user = await require_auth(request, db)
    
    if not user.is_superuser and not user.has_any_role(["admin", "super_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )
    
    return user


# ============ 公开页面 ============

@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_cookie),
):
    """登录页面。"""
    # 如果已登录，重定向到仪表盘
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "config": settings, "current_user": None},
    )


@router.get("/register", response_class=HTMLResponse, name="register")
async def register_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_cookie),
):
    """注册页面。"""
    # 如果已登录，重定向到仪表盘
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "config": settings, "current_user": None},
    )


@router.get("/logout", name="logout")
async def logout(request: Request):
    """登出并清除 Cookie。"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


# ============ 需要登录的页面 ============

@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户仪表盘页面。"""
    current_user = await get_current_user_from_cookie(request, db)
    
    if not current_user:
        return RedirectResponse(url="/login?redirect=/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "config": settings, "current_user": current_user},
    )


# ============ 管理员页面 ============

@router.get("/admin/users", response_class=HTMLResponse, name="admin_users")
async def admin_users_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户管理页面（需要管理员权限）。"""
    current_user = await get_current_user_from_cookie(request, db)
    
    if not current_user:
        return RedirectResponse(url="/login?redirect=/admin/users", status_code=status.HTTP_302_FOUND)
    
    # 检查管理员权限
    if not current_user.is_superuser and not current_user.has_any_role(["admin", "super_admin"]):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "config": settings,
                "current_user": current_user,
                "error_code": 403,
                "error_message": "权限不足",
                "error_detail": "您没有权限访问此页面。需要管理员权限。",
            },
            status_code=403,
        )
    
    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "config": settings, "current_user": current_user},
    )


@router.get("/admin/roles", response_class=HTMLResponse, name="admin_roles")
async def admin_roles_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """角色管理页面（需要管理员权限）。"""
    current_user = await get_current_user_from_cookie(request, db)
    
    if not current_user:
        return RedirectResponse(url="/login?redirect=/admin/roles", status_code=status.HTTP_302_FOUND)
    
    # 检查管理员权限
    if not current_user.is_superuser and not current_user.has_any_role(["admin", "super_admin"]):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "config": settings,
                "current_user": current_user,
                "error_code": 403,
                "error_message": "权限不足",
                "error_detail": "您没有权限访问此页面。需要管理员权限。",
            },
            status_code=403,
        )
    
    return templates.TemplateResponse(
        "admin/roles.html",
        {"request": request, "config": settings, "current_user": current_user},
    )
{%- endif %}
