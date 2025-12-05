"""
用户服务，包含业务逻辑。
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import security_manager
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import BaseService


class UserService(BaseService[User, UserCreate, UserUpdate]):
    """
    用户服务，包含用户特定的业务逻辑。
    """
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """根据邮箱地址获取用户。"""
        return await self.get_by_field(db, "email", email)
    
    async def create_user(
        self,
        db: AsyncSession,
        *,
        user_in: UserCreate,
    ) -> User:
        """
        创建新用户，并对密码进行哈希处理。
        
        参数：
            db: 数据库会话
            user_in: 用户创建数据
            
        返回：
            创建的用户实例
        """
        # 密码哈希处理
        hashed_password = security_manager.hash_password(user_in.password)
        
        # 创建用户对象
        user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
        )
        
        # 如果提供了角色则进行分配
        if user_in.role_ids:
            result = await db.execute(
                select(Role).where(Role.id.in_(user_in.role_ids))
            )
            user.roles = list(result.scalars().all())
        
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        return user
    
    async def update_user(
        self,
        db: AsyncSession,
        *,
        user: User,
        user_in: UserUpdate,
    ) -> User:
        """
        更新用户，可选择性地对密码进行哈希处理。
        
        参数：
            db: 数据库会话
            user: 现有用户实例
            user_in: 用户更新数据
            
        返回：
            更新后的用户实例
        """
        update_data = user_in.model_dump(exclude_unset=True)
        
        # 处理密码
        if "password" in update_data:
            user.hashed_password = security_manager.hash_password(
                update_data.pop("password")
            )
        
        # 处理角色
        if "role_ids" in update_data:
            role_ids = update_data.pop("role_ids")
            if role_ids is not None:
                result = await db.execute(
                    select(Role).where(Role.id.in_(role_ids))
                )
                user.roles = list(result.scalars().all())
        
        # 更新其他字段
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        return user
    
    async def authenticate(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> Optional[User]:
        """
        通过邮箱和密码认证用户。
        
        参数：
            db: 数据库会话
            email: 用户邮箱
            password: 明文密码
            
        返回：
            如果认证成功则返回用户实例，否则返回 None
        """
        user = await self.get_by_email(db, email)
        
        if not user:
            return None
        
        if not security_manager.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def is_active(self, user: User) -> bool:
        """检查用户是否活跃。"""
        return user.is_active
    
    async def is_superuser(self, user: User) -> bool:
        """检查用户是否为超级用户。"""
        return user.is_superuser
    
    async def get_users_by_role(
        self,
        db: AsyncSession,
        role_name: str,
    ) -> List[User]:
        """获取具有特定角色的所有用户。"""
        result = await db.execute(
            select(User)
            .join(User.roles)
            .where(Role.name == role_name)
        )
        return list(result.scalars().all())


# 全局服务实例
user_service = UserService()
