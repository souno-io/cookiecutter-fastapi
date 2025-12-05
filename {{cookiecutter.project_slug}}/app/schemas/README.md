# 数据模式模块 (Schemas)

本模块定义 Pydantic 数据验证模式，用于请求/响应数据的验证和序列化。

## 目录

- [模块结构](#模块结构)
- [用户模式](#用户模式)
- [认证模式](#认证模式)
- [角色模式](#角色模式)
- [通用模式](#通用模式)
- [自定义模式](#自定义模式)
- [验证器](#验证器)

---

## 模块结构

```
schemas/
├── __init__.py      # 模块导出
├── user.py          # 用户相关模式
├── auth.py          # 认证相关模式
├── role.py          # 角色相关模式
└── common.py        # 通用模式
```

---

## 用户模式

### 文件：`user.py`

定义用户相关的请求和响应模式。

### 模式定义

```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    """用户基础模式"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")

class UserCreate(UserBase):
    """用户创建模式（请求）"""
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "email": "zhangsan@example.com",
                "full_name": "张三",
                "password": "SecurePass123!"
            }
        }

class UserUpdate(BaseModel):
    """用户更新模式（请求）"""
    full_name: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    
class UserPasswordUpdate(BaseModel):
    """密码更新模式"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, description="新密码")

class UserResponse(UserBase):
    """用户响应模式"""
    id: int
    is_active: bool
    is_superuser: bool
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # 支持 ORM 模型转换

class UserInDB(UserResponse):
    """数据库用户模式（包含敏感信息）"""
    hashed_password: str
    last_login: Optional[datetime] = None

class UserWithRoles(UserResponse):
    """用户及角色响应模式"""
    roles: List["RoleResponse"] = []
```

### 使用示例

```python
from app.schemas import UserCreate, UserResponse, UserUpdate

# 请求验证
@router.post("/users", response_model=UserResponse)
async def create_user(user_in: UserCreate):
    # user_in 已经过 Pydantic 验证
    # user_in.username, user_in.email, user_in.password
    user = await user_service.create(user_in)
    return user  # 自动序列化为 UserResponse

# 响应转换
user = await db.get(User, 1)
response = UserResponse.model_validate(user)  # ORM 转 Schema

# 部分更新
@router.patch("/users/{user_id}")
async def update_user(user_id: int, user_in: UserUpdate):
    # 只更新提供的字段
    update_data = user_in.model_dump(exclude_unset=True)
    # update_data = {"full_name": "新名字"}  # 只包含传入的字段
```

---

## 认证模式

### 文件：`auth.py`

定义认证相关的请求和响应模式。

### 模式定义

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123",
                "remember_me": False
            }
        }

class Token(BaseModel):
    """令牌响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")

class TokenPayload(BaseModel):
    """令牌载荷"""
    sub: str = Field(..., description="用户ID")
    exp: int = Field(..., description="过期时间戳")
    iat: int = Field(..., description="签发时间戳")
    type: str = Field(..., description="令牌类型")

class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")

class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: EmailStr = Field(..., description="注册邮箱")

class PasswordResetConfirm(BaseModel):
    """密码重置确认"""
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, description="新密码")

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次输入的密码不一致")
        return v
```

### 使用示例

```python
from app.schemas import LoginRequest, Token, TokenPayload

# 登录
@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest):
    user = await auth_service.authenticate(
        credentials.username,
        credentials.password
    )
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in=1800
    )

# 解析令牌
payload = TokenPayload(**jwt.decode(token, SECRET_KEY))
user_id = payload.sub
```

---

## 角色模式

### 文件：`role.py`

定义角色相关的请求和响应模式。

### 模式定义

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RoleBase(BaseModel):
    """角色基础模式"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")

class RoleCreate(RoleBase):
    """角色创建模式"""
    permissions: List[str] = Field(default=[], description="权限列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "editor",
                "display_name": "编辑者",
                "description": "内容编辑权限",
                "permissions": ["content:read", "content:write"]
            }
        }

class RoleUpdate(BaseModel):
    """角色更新模式"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleResponse(RoleBase):
    """角色响应模式"""
    id: int
    permissions: List[str]
    is_system: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class RoleWithUsers(RoleResponse):
    """角色及用户响应模式"""
    users_count: int = 0
    users: List["UserResponse"] = []

class AssignRoleRequest(BaseModel):
    """分配角色请求"""
    user_id: int = Field(..., description="用户ID")
    role_id: int = Field(..., description="角色ID")
```

---

## 通用模式

### 文件：`common.py`

定义通用的响应模式。

### 模式定义

```python
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional, Any
from datetime import datetime

T = TypeVar("T")

class MessageResponse(BaseModel):
    """消息响应"""
    success: bool = True
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功"
            }
        }

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: dict = Field(..., description="错误详情")
    request_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "数据验证失败",
                    "details": {"field": "email", "reason": "格式不正确"}
                },
                "request_id": "abc123"
            }
        }

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="应用版本")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: dict = Field(default={}, description="依赖服务状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-01T00:00:00Z",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                    "celery": "ok"
                }
            }
        }

class PageInfo(BaseModel):
    """分页信息"""
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页数量")
    total: int = Field(..., description="总数量")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    data: List[T] = Field(..., description="数据列表")
    pagination: PageInfo = Field(..., description="分页信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": [],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 100,
                    "pages": 5,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }

class IDResponse(BaseModel):
    """ID 响应"""
    id: int = Field(..., description="资源ID")

class BatchResponse(BaseModel):
    """批量操作响应"""
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    errors: List[dict] = Field(default=[], description="错误详情")
```

### 使用示例

```python
from app.schemas import PaginatedResponse, MessageResponse, PageInfo
from app.schemas import UserResponse

# 分页响应
@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(page: int = 1, per_page: int = 20):
    users, total = await user_service.get_paginated(page, per_page)
    return PaginatedResponse(
        data=users,
        pagination=PageInfo(
            page=page,
            per_page=per_page,
            total=total,
            pages=(total + per_page - 1) // per_page,
            has_next=page * per_page < total,
            has_prev=page > 1
        )
    )

# 消息响应
@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(user_id: int):
    await user_service.delete(user_id)
    return MessageResponse(message="用户删除成功")
```

---

## 自定义模式

### 创建新模式

```python
# schemas/article.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ArticleStatus(str, Enum):
    """文章状态枚举"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ArticleBase(BaseModel):
    """文章基础模式"""
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    content: str = Field(..., min_length=10, description="内容")
    summary: Optional[str] = Field(None, max_length=500, description="摘要")
    tags: List[str] = Field(default=[], max_items=10, description="标签")
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        # 去重并限制标签长度
        return list(set(tag[:20] for tag in v))

class ArticleCreate(ArticleBase):
    """文章创建模式"""
    category_id: Optional[int] = None
    cover_image: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "FastAPI 入门教程",
                "content": "这是一篇关于 FastAPI 的入门教程...",
                "summary": "快速上手 FastAPI 框架",
                "tags": ["Python", "FastAPI", "Web开发"],
                "category_id": 1
            }
        }

class ArticleUpdate(BaseModel):
    """文章更新模式"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    summary: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None
    category_id: Optional[int] = None
    status: Optional[ArticleStatus] = None

class ArticleResponse(ArticleBase):
    """文章响应模式"""
    id: int
    slug: str
    status: ArticleStatus
    view_count: int
    author_id: int
    category_id: Optional[int]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ArticleDetail(ArticleResponse):
    """文章详情模式（包含关联数据）"""
    author: "UserResponse"
    category: Optional["CategoryResponse"] = None
    comments_count: int = 0
```

### 注册新模式

```python
# schemas/__init__.py
from app.schemas.article import (
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleDetail,
    ArticleStatus,
)

__all__ = [
    # ... 其他导出
    "ArticleCreate",
    "ArticleUpdate", 
    "ArticleResponse",
    "ArticleDetail",
    "ArticleStatus",
]
```

---

## 验证器

### 字段验证器

```python
from pydantic import BaseModel, field_validator, model_validator
import re

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str
    phone: Optional[str] = None
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """验证用户名"""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]{2,49}$", v):
            raise ValueError("用户名必须以字母开头，只能包含字母、数字和下划线")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError("密码至少8个字符")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含小写字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """验证手机号"""
        if v and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v
    
    @model_validator(mode="after")
    def check_passwords_match(self):
        """验证两次密码一致"""
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self
```

### 自定义类型

```python
from pydantic import BeforeValidator
from typing import Annotated

def validate_phone_number(v: str) -> str:
    """手机号验证器"""
    if not re.match(r"^1[3-9]\d{9}$", v):
        raise ValueError("手机号格式不正确")
    return v

def validate_id_card(v: str) -> str:
    """身份证号验证器"""
    if not re.match(r"^\d{17}[\dXx]$", v):
        raise ValueError("身份证号格式不正确")
    return v.upper()

# 自定义类型
PhoneNumber = Annotated[str, BeforeValidator(validate_phone_number)]
IDCard = Annotated[str, BeforeValidator(validate_id_card)]

# 使用自定义类型
class UserProfile(BaseModel):
    phone: PhoneNumber
    id_card: IDCard
```

---

## 注意事项

1. **验证优先**: 所有外部输入都应通过 Pydantic 模式验证
2. **响应模型**: 使用 `response_model` 参数确保响应格式一致
3. **ORM 模式**: 设置 `from_attributes = True` 以支持 ORM 模型转换
4. **示例文档**: 使用 `json_schema_extra` 提供 API 文档示例
5. **字段描述**: 使用 `Field` 的 `description` 参数添加字段说明
6. **敏感字段**: 响应模式中排除敏感字段（如密码哈希）
7. **类型提示**: 使用正确的类型提示提高代码可读性
