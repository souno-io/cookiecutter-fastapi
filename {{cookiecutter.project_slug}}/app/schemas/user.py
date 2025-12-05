"""
用户数据模式定义。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """用户基础模式，包含通用字段。"""
    
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = True
    avatar: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(BaseModel):
    """创建新用户的数据模式。"""
    
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    role_ids: Optional[List[int]] = None


class UserUpdate(BaseModel):
    """更新现有用户的数据模式。"""
    
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    role_ids: Optional[List[int]] = None


class UserResponse(BaseModel):
    """用户响应数据模式。"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    avatar: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    roles: List["RoleSimple"] = []


class UserInDB(UserResponse):
    """数据库中的用户模式（包含哈希密码）。"""
    
    hashed_password: str


class UserSimple(BaseModel):
    """简化的用户模式，用于嵌套响应。"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    full_name: Optional[str] = None


class RoleSimple(BaseModel):
    """简化的角色模式，用于用户响应。"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str


# 更新前向引用
UserResponse.model_rebuild()
