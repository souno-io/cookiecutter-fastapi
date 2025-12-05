"""
角色管理端点。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse, RoleAssign
from app.schemas.common import PaginatedResponse, MessageResponse
from app.api.deps import get_current_superuser, RoleChecker, get_current_active_user

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[RoleResponse],
    summary="List Roles",
    description="Get a paginated list of roles",
    dependencies=[Depends(RoleChecker(["admin", "super_admin"]))],
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[RoleResponse]:
    """
    获取分页的角色列表。
    
    需要管理员角色。
    """
    query = select(Role)
    count_query = select(func.count()).select_from(Role)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(Role.name.ilike(search_filter))
        count_query = count_query.where(Role.name.ilike(search_filter))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size).order_by(Role.name)
    
    result = await db.execute(query)
    roles = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[RoleResponse.model_validate(r) for r in roles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get Role",
    description="Get a specific role by ID",
    dependencies=[Depends(RoleChecker(["admin", "super_admin"]))],
)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RoleResponse:
    """根据 ID 获取角色。"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    
    return RoleResponse.model_validate(role)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
    description="Create a new role (superuser only)",
)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> RoleResponse:
    """
    创建新角色。
    
    只有超级用户才能创建角色。
    """
    # 检查角色名称是否存在
    result = await db.execute(select(Role).where(Role.name == role_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists",
        )
    
    # 创建角色
    permissions_str = None
    if role_data.permissions:
        permissions_str = ",".join(role_data.permissions)
    
    new_role = Role(
        name=role_data.name,
        description=role_data.description,
        permissions=permissions_str,
    )
    
    db.add(new_role)
    await db.flush()
    await db.refresh(new_role)
    
    return RoleResponse.model_validate(new_role)


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update Role",
    description="Update an existing role (superuser only)",
)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> RoleResponse:
    """
    更新角色。
    
    只有超级用户才能更新角色。
    """
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    
    update_data = role_data.model_dump(exclude_unset=True)
    
    # 如果更新名称，检查名称唯一性
    if "name" in update_data and update_data["name"] != role.name:
        result = await db.execute(
            select(Role).where(Role.name == update_data["name"])
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists",
            )
    
    # 处理权限
    if "permissions" in update_data:
        permissions = update_data.pop("permissions")
        if permissions is not None:
            role.permissions = ",".join(permissions)
    
    # 更新其他字段
    for field, value in update_data.items():
        if hasattr(role, field):
            setattr(role, field, value)
    
    db.add(role)
    await db.flush()
    await db.refresh(role)
    
    return RoleResponse.model_validate(role)


@router.delete(
    "/{role_id}",
    response_model=MessageResponse,
    summary="Delete Role",
    description="Delete a role (superuser only)",
)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> MessageResponse:
    """
    删除角色。
    
    只有超级用户才能删除角色。
    """
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    
    await db.delete(role)
    
    return MessageResponse(message="Role deleted successfully")


@router.post(
    "/assign",
    response_model=MessageResponse,
    summary="Assign Roles to User",
    description="Assign roles to a user (superuser only)",
)
async def assign_roles(
    data: RoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> MessageResponse:
    """
    为用户分配角色。
    
    替换所有现有的角色分配。
    """
    # 获取用户
    result = await db.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # 获取角色
    result = await db.execute(select(Role).where(Role.id.in_(data.role_ids)))
    roles = result.scalars().all()
    
    if len(roles) != len(data.role_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some roles not found",
        )
    
    # 分配角色
    user.roles = list(roles)
    db.add(user)
    
    return MessageResponse(message="Roles assigned successfully")
