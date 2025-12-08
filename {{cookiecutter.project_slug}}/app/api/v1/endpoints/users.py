"""
用户管理端点。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.security import security_manager
from app.db.session import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import PaginatedResponse, MessageResponse
from app.api.deps import get_current_active_user, get_current_superuser, RoleChecker

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="用户列表",
    description="获取分页的用户列表",
    dependencies=[Depends(RoleChecker(["admin", "super_admin"]))],
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="按邮箱或姓名搜索"),
    is_active: Optional[bool] = Query(None, description="按激活状态筛选"),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[UserResponse]:
    """
    获取分页的用户列表。
    
    需要管理员角色。
    """
    # 构建查询
    query = select(User)
    count_query = select(func.count()).select_from(User)
    
    # 应用过滤器
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter))
        )
        count_query = count_query.where(
            (User.email.ilike(search_filter)) | 
            (User.full_name.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 应用分页
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size).order_by(User.created_at.desc())
    
    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户",
    description="根据 ID 获取特定用户",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    根据 ID 获取用户。
    
    普通用户只能查看自己的个人资料。
    管理员可以查看任何用户。
    """
    # 检查权限
    if not current_user.is_superuser and current_user.id != user_id:
        if not current_user.has_any_role(["admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    return UserResponse.model_validate(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
    description="创建新用户（仅管理员）",
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> UserResponse:
    """
    创建新用户。
    
    只有超级用户才能创建具有特定角色的新用户。
    """
    # 检查邮箱是否存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )
    
    # 创建用户
    hashed_password = security_manager.hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
    )
    
    # 如果提供了角色则进行分配
    if user_data.role_ids:
        result = await db.execute(
            select(Role).where(Role.id.in_(user_data.role_ids))
        )
        roles = result.scalars().all()
        new_user.roles = list(roles)
    
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    return UserResponse.model_validate(new_user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="更新用户",
    description="更新现有用户",
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    更新用户个人资料。
    
    用户可以更新自己的个人资料。
    管理员可以更新任何用户。
    """
    # 检查权限
    is_self = current_user.id == user_id
    is_admin = current_user.is_superuser or current_user.has_any_role(["admin"])
    
    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # 更新字段
    update_data = user_data.model_dump(exclude_unset=True)
    
    # 只有管理员才能更新角色
    if "role_ids" in update_data and is_admin:
        role_ids = update_data.pop("role_ids")
        if role_ids is not None:
            result = await db.execute(
                select(Role).where(Role.id.in_(role_ids))
            )
            user.roles = list(result.scalars().all())
    elif "role_ids" in update_data:
        update_data.pop("role_ids")
    
    # 处理密码更新
    if "password" in update_data:
        user.hashed_password = security_manager.hash_password(update_data.pop("password"))
    
    # 更新其他字段
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="删除用户",
    description="删除用户（仅超级用户）",
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> MessageResponse:
    """
    删除用户。
    
    只有超级用户才能删除用户。
    不能删除自己。
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    await db.delete(user)
    
    return MessageResponse(message="用户删除成功")
