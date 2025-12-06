"""
用户模型定义。
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.role import Role


class User(Base):
    """
    用户模型，用于认证和授权。
    
    属性:
        email: 用户邮箱地址（唯一）
        hashed_password: bcrypt 哈希密码
        full_name: 用户显示名称
        is_active: 用户账户是否活跃
        is_superuser: 用户是否拥有超级用户权限
        avatar: 用户头像 URL
        bio: 用户简介/描述
        roles: 分配给用户的角色列表
    """
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 关联关系
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
    
    @property
    def role_names(self) -> list[str]:
        """获取角色名称列表。"""
        return [role.name for role in self.roles]
    
    def has_role(self, role_name: str) -> bool:
        """检查用户是否拥有特定角色。"""
        return role_name in self.role_names
    
    def has_any_role(self, role_names: list[str]) -> bool:
        """检查用户是否拥有指定角色中的任一个。"""
        return any(role in self.role_names for role in role_names)
