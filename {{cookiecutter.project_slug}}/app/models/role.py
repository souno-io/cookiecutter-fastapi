"""
RBAC 角色模型定义。
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


# 用户-角色多对多关联表
class UserRole(Base):
    """用户和角色的关联表。"""
    
    __tablename__ = "user_roles"
    
    # 覆盖基类的 id，使用复合主键
    id: Mapped[int] = mapped_column(Integer, primary_key=False, autoincrement=False, default=0)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Role(Base):
    """
    RBAC 角色模型。
    
    属性:
        name: 角色名称（唯一）
        description: 角色描述
        permissions: 逗号分隔的权限字符串列表
        users: 分配到此角色的用户
    """
    
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 以逗号分隔的字符串存储
    
    # 关联关系
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"
    
    @property
    def permission_list(self) -> list[str]:
        """获取权限列表。"""
        if not self.permissions:
            return []
        return [p.strip() for p in self.permissions.split(",") if p.strip()]
    
    def add_permission(self, permission: str) -> None:
        """向角色添加权限。"""
        current = set(self.permission_list)
        current.add(permission)
        self.permissions = ",".join(sorted(current))
    
    def remove_permission(self, permission: str) -> None:
        """从角色移除权限。"""
        current = set(self.permission_list)
        current.discard(permission)
        self.permissions = ",".join(sorted(current))
    
    def has_permission(self, permission: str) -> bool:
        """检查角色是否拥有特定权限。"""
        return permission in self.permission_list
