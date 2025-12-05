# API 模块 (API)

本模块提供 RESTful API 端点定义、请求验证和依赖注入。

## 目录

- [模块结构](#模块结构)
- [依赖注入](#依赖注入)
- [路由配置](#路由配置)
- [端点开发](#端点开发)
- [请求响应](#请求响应)
- [API 版本管理](#api-版本管理)

---

## 模块结构

```
api/
├── __init__.py          # 模块导出
├── deps.py              # 公共依赖注入
└── v1/
    ├── __init__.py      # v1 版本导出
    ├── router.py        # v1 路由聚合
    └── endpoints/
        ├── __init__.py
        ├── auth.py      # 认证端点
        ├── users.py     # 用户端点
        ├── roles.py     # 角色端点
        ├── files.py     # 文件端点
        └── health.py    # 健康检查端点
```

---

## 依赖注入

### 文件：`deps.py`

提供公共依赖注入函数，用于认证、授权和数据库访问。

### 用户认证依赖

```python
from fastapi import Depends
from app.api.deps import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
)

# 获取当前用户（可能未激活）
@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user

# 获取当前活跃用户
@router.get("/dashboard")
async def dashboard(
    current_user: User = Depends(get_current_active_user)
):
    return {"user": current_user.username}

# 获取超级管理员
@router.get("/admin/settings")
async def admin_settings(
    current_user: User = Depends(get_current_superuser)
):
    return {"admin": current_user.username}
```

### 数据库会话依赖

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db

@router.get("/items")
async def get_items(
    db: AsyncSession = Depends(get_db)
):
    # 使用数据库会话
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### 分页依赖

```python
from app.utils.pagination import PaginationParams

@router.get("/users")
async def list_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # pagination.page: 当前页码
    # pagination.per_page: 每页数量
    # pagination.skip: 偏移量
    users = await get_users(db, skip=pagination.skip, limit=pagination.per_page)
    return users
```

### 自定义依赖

```python
from fastapi import Depends, Query

def pagination_params(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量")
):
    """分页参数依赖"""
    return {"page": page, "per_page": per_page, "skip": (page - 1) * per_page}

def search_params(
    q: str = Query(None, min_length=1, max_length=100, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", regex="^(asc|desc)$", description="排序方向")
):
    """搜索参数依赖"""
    return {"q": q, "sort_by": sort_by, "order": order}

@router.get("/articles")
async def list_articles(
    pagination: dict = Depends(pagination_params),
    search: dict = Depends(search_params)
):
    return {"pagination": pagination, "search": search}
```

---

## 路由配置

### 文件：`v1/router.py`

聚合所有 v1 版本的路由。

### 路由注册

```python
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, roles, files, health

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["用户管理"]
)
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["角色管理"]
)
api_router.include_router(
    files.router,
    prefix="/files",
    tags=["文件管理"]
)
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["健康检查"]
)
```

### 在 main.py 中挂载

```python
from fastapi import FastAPI
from app.api.v1.router import api_router

app = FastAPI()

# 挂载 v1 API
app.include_router(api_router, prefix="/api/v1")
```

---

## 端点开发

### 认证端点示例

```python
# endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import Token, LoginRequest
from app.services import AuthService

router = APIRouter()

@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录接口
    
    - **username**: 用户名或邮箱
    - **password**: 密码
    
    返回 JWT 访问令牌和刷新令牌
    """
    auth_service = AuthService(db)
    user = await auth_service.authenticate(
        form_data.username,
        form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    return auth_service.create_tokens(user)

@router.post("/refresh", response_model=Token, summary="刷新令牌")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """使用刷新令牌获取新的访问令牌"""
    auth_service = AuthService(db)
    return await auth_service.refresh_tokens(refresh_token)

@router.post("/logout", summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """用户登出，使当前令牌失效"""
    # 可以将令牌加入黑名单
    return {"message": "登出成功"}
```

### CRUD 端点示例

```python
# endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.services import UserService
from app.api.deps import get_current_active_user, get_current_superuser
from app.core.rbac import require_permissions, Permission

router = APIRouter()

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="获取用户列表"
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USER_READ))
):
    """
    获取用户列表
    
    需要 USER_READ 权限
    """
    service = UserService(db)
    return await service.get_multi(skip=skip, limit=limit)

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户详情"
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USER_READ))
):
    """获取指定用户的详细信息"""
    service = UserService(db)
    user = await service.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户"
)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USER_CREATE))
):
    """
    创建新用户
    
    需要 USER_CREATE 权限
    """
    service = UserService(db)
    
    # 检查用户名是否已存在
    if await service.get_by_username(user_in.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if await service.get_by_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册"
        )
    
    return await service.create(user_in)

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="更新用户"
)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USER_UPDATE))
):
    """更新用户信息"""
    service = UserService(db)
    user = await service.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return await service.update(user, user_in)

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户"
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permissions(Permission.USER_DELETE))
):
    """删除用户"""
    service = UserService(db)
    user = await service.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    await service.delete(user)
```

---

## 请求响应

### 请求体验证

```python
from pydantic import BaseModel, Field, validator

class CreateArticleRequest(BaseModel):
    """创建文章请求"""
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    content: str = Field(..., min_length=10, description="文章内容")
    tags: list[str] = Field(default=[], max_items=10, description="标签列表")
    published: bool = Field(default=False, description="是否发布")
    
    @validator("title")
    def validate_title(cls, v):
        if v.strip() != v:
            raise ValueError("标题不能以空格开头或结尾")
        return v

@router.post("/articles")
async def create_article(
    article: CreateArticleRequest,
    db: AsyncSession = Depends(get_db)
):
    # article 已经过验证
    return await ArticleService(db).create(article)
```

### 路径参数验证

```python
from fastapi import Path

@router.get("/users/{user_id}")
async def get_user(
    user_id: int = Path(..., gt=0, description="用户ID，必须大于0")
):
    return {"user_id": user_id}

@router.get("/items/{item_code}")
async def get_item(
    item_code: str = Path(
        ...,
        min_length=5,
        max_length=10,
        regex="^[A-Z]{2}[0-9]{3,8}$",
        description="商品编码，如 AB12345"
    )
):
    return {"item_code": item_code}
```

### 查询参数验证

```python
from fastapi import Query
from typing import Optional
from datetime import date

@router.get("/orders")
async def list_orders(
    status: Optional[str] = Query(
        None,
        regex="^(pending|paid|shipped|completed)$",
        description="订单状态"
    ),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    min_amount: float = Query(0, ge=0, description="最小金额"),
    max_amount: float = Query(999999, le=999999, description="最大金额")
):
    return {
        "status": status,
        "date_range": [start_date, end_date],
        "amount_range": [min_amount, max_amount]
    }
```

### 统一响应格式

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")

class ResponseBase(BaseModel, Generic[T]):
    """统一响应基类"""
    success: bool = True
    data: Optional[T] = None
    message: str = "操作成功"

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    data: List[T]
    total: int
    page: int
    per_page: int
    pages: int

# 使用示例
@router.get("/users", response_model=ResponseBase[List[UserResponse]])
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await UserService(db).get_multi()
    return ResponseBase(data=users, message="获取成功")
```

---

## API 版本管理

### 多版本支持

```
api/
├── v1/
│   ├── router.py
│   └── endpoints/
│       └── users.py      # v1 用户接口
└── v2/
    ├── router.py
    └── endpoints/
        └── users.py      # v2 用户接口（新特性）
```

### 在 main.py 中配置

```python
from fastapi import FastAPI
from app.api.v1.router import api_router as api_v1
from app.api.v2.router import api_router as api_v2

app = FastAPI()

# 挂载多个版本
app.include_router(api_v1, prefix="/api/v1")
app.include_router(api_v2, prefix="/api/v2")
```

### 版本迁移策略

```python
# v1/endpoints/users.py - 旧版本
@router.get("/{user_id}")
async def get_user_v1(user_id: int):
    """v1: 返回基础用户信息"""
    return {"id": user_id, "name": "用户"}

# v2/endpoints/users.py - 新版本
@router.get("/{user_id}")
async def get_user_v2(user_id: int):
    """v2: 返回详细用户信息，包含头像和个人简介"""
    return {
        "id": user_id,
        "name": "用户",
        "avatar": "https://...",
        "bio": "个人简介",
        "social_links": []
    }
```

---

## 最佳实践

### 1. 路由命名规范

```python
# RESTful 风格
GET    /users          # 获取列表
POST   /users          # 创建
GET    /users/{id}     # 获取详情
PUT    /users/{id}     # 全量更新
PATCH  /users/{id}     # 部分更新
DELETE /users/{id}     # 删除

# 资源嵌套
GET    /users/{user_id}/articles        # 获取用户的文章列表
POST   /users/{user_id}/articles        # 为用户创建文章
DELETE /users/{user_id}/articles/{id}   # 删除用户的文章
```

### 2. 错误处理

```python
from fastapi import HTTPException
from app.core.exceptions import NotFoundError, BusinessError

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await UserService(db).get(user_id)
    
    # 方式1: 使用 HTTPException
    if not user:
        raise HTTPException(
            status_code=404,
            detail="用户不存在"
        )
    
    # 方式2: 使用自定义异常（推荐）
    if not user:
        raise NotFoundError(
            message="用户不存在",
            resource="user",
            resource_id=user_id
        )
    
    return user
```

### 3. 文档注释

```python
@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    summary="创建新用户",
    description="创建一个新的用户账户，需要管理员权限",
    responses={
        201: {"description": "用户创建成功"},
        400: {"description": "请求参数错误"},
        409: {"description": "用户名或邮箱已存在"},
        403: {"description": "权限不足"}
    }
)
async def create_user(user: UserCreate):
    """
    创建新用户
    
    - **username**: 用户名，3-50个字符
    - **email**: 邮箱地址
    - **password**: 密码，至少8个字符
    - **full_name**: 可选，用户全名
    """
    pass
```

---

## 注意事项

1. **依赖注入**: 合理使用依赖注入，避免重复代码
2. **权限检查**: 所有敏感端点都应添加权限验证
3. **参数验证**: 使用 Pydantic 模型和 Field 进行请求验证
4. **错误处理**: 使用自定义异常，返回统一格式的错误响应
5. **API 文档**: 为所有端点添加详细的文档注释
6. **版本管理**: 使用 URL 前缀区分 API 版本
