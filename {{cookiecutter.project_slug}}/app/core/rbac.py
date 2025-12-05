"""
基于角色的访问控制 (RBAC) 实现。

提供：
- 权限定义
- 角色-权限映射
- 访问控制装饰器和依赖
"""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set, Union

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel


class Permission(str, Enum):
    """
    系统权限枚举。
    
    命名规范：资源_操作
    """
    # 用户权限
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # 角色权限
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_ASSIGN = "role:assign"
    
    # 内容/资源权限（示例）
    CONTENT_READ = "content:read"
    CONTENT_CREATE = "content:create"
    CONTENT_UPDATE = "content:update"
    CONTENT_DELETE = "content:delete"
    
    # 管理员权限
    ADMIN_ACCESS = "admin:access"
    ADMIN_SETTINGS = "admin:settings"
    SYSTEM_MANAGE = "system:manage"


class RoleType(str, Enum):
    """默认系统角色。"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class RolePermissions(BaseModel):
    """角色及其关联的权限。"""
    role: str
    permissions: Set[str]
    description: Optional[str] = None


class RBACManager:
    """
    RBAC 管理器，用于处理基于角色的访问控制。
    
    功能：
    - 角色-权限映射管理
    - 权限检查
    - 层级角色支持
    """
    
    # 默认角色-权限映射
    DEFAULT_ROLE_PERMISSIONS: dict = {
        RoleType.SUPER_ADMIN: {
            Permission.USER_READ, Permission.USER_CREATE, Permission.USER_UPDATE, 
            Permission.USER_DELETE, Permission.USER_LIST,
            Permission.ROLE_READ, Permission.ROLE_CREATE, Permission.ROLE_UPDATE,
            Permission.ROLE_DELETE, Permission.ROLE_ASSIGN,
            Permission.CONTENT_READ, Permission.CONTENT_CREATE, Permission.CONTENT_UPDATE,
            Permission.CONTENT_DELETE,
            Permission.ADMIN_ACCESS, Permission.ADMIN_SETTINGS, Permission.SYSTEM_MANAGE,
        },
        RoleType.ADMIN: {
            Permission.USER_READ, Permission.USER_CREATE, Permission.USER_UPDATE, 
            Permission.USER_LIST,
            Permission.ROLE_READ, Permission.ROLE_ASSIGN,
            Permission.CONTENT_READ, Permission.CONTENT_CREATE, Permission.CONTENT_UPDATE,
            Permission.CONTENT_DELETE,
            Permission.ADMIN_ACCESS,
        },
        RoleType.MODERATOR: {
            Permission.USER_READ, Permission.USER_LIST,
            Permission.CONTENT_READ, Permission.CONTENT_CREATE, Permission.CONTENT_UPDATE,
        },
        RoleType.USER: {
            Permission.USER_READ,
            Permission.CONTENT_READ, Permission.CONTENT_CREATE,
        },
        RoleType.GUEST: {
            Permission.CONTENT_READ,
        },
    }
    
    # 角色层级（高级角色继承低级角色的权限）
    ROLE_HIERARCHY: dict = {
        RoleType.SUPER_ADMIN: [RoleType.ADMIN, RoleType.MODERATOR, RoleType.USER, RoleType.GUEST],
        RoleType.ADMIN: [RoleType.MODERATOR, RoleType.USER, RoleType.GUEST],
        RoleType.MODERATOR: [RoleType.USER, RoleType.GUEST],
        RoleType.USER: [RoleType.GUEST],
        RoleType.GUEST: [],
    }
    
    def __init__(self):
        self._role_permissions: dict = {}
        self._custom_permissions: dict = {}
        self._initialize_default_permissions()
    
    def _initialize_default_permissions(self) -> None:
        """初始化默认角色-权限映射。"""
        for role, permissions in self.DEFAULT_ROLE_PERMISSIONS.items():
            self._role_permissions[role.value] = {p.value for p in permissions}
    
    def get_role_permissions(self, role: Union[str, RoleType]) -> Set[str]:
        """
        Get all permissions for a role including inherited permissions.
        
        Args:
            role: Role name or RoleType enum
            
        Returns:
            Set of permission strings
        """
        role_value = role.value if isinstance(role, RoleType) else role
        permissions = set(self._role_permissions.get(role_value, set()))
        
        # 从角色层级中添加继承的权限
        try:
            role_enum = RoleType(role_value)
            for inherited_role in self.ROLE_HIERARCHY.get(role_enum, []):
                permissions.update(self._role_permissions.get(inherited_role.value, set()))
        except ValueError:
            pass  # 没有层级的自定义角色
        
        return permissions
    
    def has_permission(
        self, 
        user_roles: List[str], 
        required_permissions: Union[str, List[str], Permission, List[Permission]],
        require_all: bool = True,
    ) -> bool:
        """
        Check if user has required permission(s).
        
        Args:
            user_roles: List of user's role names
            required_permissions: Required permission(s)
            require_all: If True, user must have all permissions; if False, any one is sufficient
            
        Returns:
            True if permission check passes
        """
        # 将权限规范化为字符串列表
        if isinstance(required_permissions, (str, Permission)):
            required_permissions = [required_permissions]
        
        required = {
            p.value if isinstance(p, Permission) else p 
            for p in required_permissions
        }
        
        # 从所有角色中收集用户的所有权限
        user_permissions: Set[str] = set()
        for role in user_roles:
            user_permissions.update(self.get_role_permissions(role))
        
        # 检查权限
        if require_all:
            return required.issubset(user_permissions)
        else:
            return bool(required.intersection(user_permissions))
    
    def add_custom_role(
        self, 
        role_name: str, 
        permissions: Set[Union[str, Permission]],
        inherit_from: Optional[str] = None,
    ) -> None:
        """
        Add a custom role with permissions.
        
        Args:
            role_name: Name of the new role
            permissions: Set of permissions for the role
            inherit_from: Role to inherit permissions from
        """
        normalized_permissions = {
            p.value if isinstance(p, Permission) else p 
            for p in permissions
        }
        
        if inherit_from and inherit_from in self._role_permissions:
            normalized_permissions.update(self._role_permissions[inherit_from])
        
        self._role_permissions[role_name] = normalized_permissions
    
    def add_permission_to_role(
        self, 
        role: Union[str, RoleType], 
        permission: Union[str, Permission],
    ) -> None:
        """为现有角色添加权限。"""
        role_value = role.value if isinstance(role, RoleType) else role
        perm_value = permission.value if isinstance(permission, Permission) else permission
        
        if role_value in self._role_permissions:
            self._role_permissions[role_value].add(perm_value)
    
    def remove_permission_from_role(
        self, 
        role: Union[str, RoleType], 
        permission: Union[str, Permission],
    ) -> None:
        """从角色中移除权限。"""
        role_value = role.value if isinstance(role, RoleType) else role
        perm_value = permission.value if isinstance(permission, Permission) else permission
        
        if role_value in self._role_permissions:
            self._role_permissions[role_value].discard(perm_value)


# 全局 RBAC 管理器实例
rbac_manager = RBACManager()


def require_permissions(
    permissions: Union[str, List[str], Permission, List[Permission]],
    require_all: bool = True,
) -> Callable:
    """
    Decorator to require specific permissions for an endpoint.
    
    Usage:
        @router.get("/admin")
        @require_permissions([Permission.ADMIN_ACCESS])
        async def admin_endpoint(current_user: User = Depends(get_current_user)):
            ...
    
    Args:
        permissions: Required permission(s)
        require_all: If True, all permissions required; if False, any one is sufficient
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取当前用户（由 Depends 注入）
            current_user = kwargs.get("current_user")
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            
            # 获取用户角色
            user_roles = getattr(current_user, "roles", [])
            if not user_roles:
                user_roles = [getattr(current_user, "role", "guest")]
            
            # 将角色规范化为字符串列表
            role_names = [
                r.name if hasattr(r, "name") else str(r) 
                for r in user_roles
            ]
            
            # Check permissions
            if not rbac_manager.has_permission(role_names, permissions, require_all):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class PermissionChecker:
    """
    Dependency class for checking permissions in FastAPI routes.
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            _: bool = Depends(PermissionChecker([Permission.ADMIN_ACCESS])),
            current_user: User = Depends(get_current_user)
        ):
            ...
    """
    
    def __init__(
        self, 
        permissions: Union[str, List[str], Permission, List[Permission]],
        require_all: bool = True,
    ):
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(self, current_user = None) -> bool:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        
        user_roles = getattr(current_user, "roles", [])
        if not user_roles:
            user_roles = [getattr(current_user, "role", "guest")]
        
        role_names = [
            r.name if hasattr(r, "name") else str(r) 
            for r in user_roles
        ]
        
        if not rbac_manager.has_permission(role_names, self.permissions, self.require_all):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return True
