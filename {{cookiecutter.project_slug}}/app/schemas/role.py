"""
角色数据模式定义。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    """角色基础模式。"""
    
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    permissions: Optional[str] = None


class RoleCreate(BaseModel):
    """创建新角色的数据模式。"""
    
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None  # 权限字符串列表


class RoleUpdate(BaseModel):
    """更新现有角色的数据模式。"""
    
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(BaseModel):
    """角色响应数据模式。"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    permissions: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def permission_list(self) -> List[str]:
        """获取权限列表。"""
        if not self.permissions:
            return []
        return [p.strip() for p in self.permissions.split(",") if p.strip()]


class RoleAssign(BaseModel):
    """分配角色给用户的数据模式。"""
    
    user_id: int
    role_ids: List[int]
