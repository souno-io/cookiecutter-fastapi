# {{ cookiecutter.project_name }}

{{ cookiecutter.project_description }}

---

## 目录

- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 接口](#api-接口)
- [认证与授权](#认证与授权)
- [服务层使用指南](#服务层使用指南)
- [数据库操作](#数据库操作)
- [测试](#测试)
- [部署](#部署)
- [开发规范](#开发规范)

---

## 功能特性

### 核心框架

| 功能 | 说明 |
|------|------|
| **FastAPI** | 现代化、高性能的异步 Web 框架，内置 OpenAPI 文档生成 |
| **SQLAlchemy 2.0** | 全新的异步 ORM，完整的类型注解支持 |
| **Pydantic v2** | 数据验证和序列化，完美集成 FastAPI |
| **Alembic** | 数据库版本控制和迁移管理 |

### 安全认证

| 功能 | 说明 |
|------|------|
| **JWT 认证** | 基于 JSON Web Token 的无状态认证，支持访问令牌和刷新令牌 |
| **RBAC** | 基于角色的访问控制，细粒度权限管理 |
| **密码哈希** | 使用 bcrypt 算法安全存储密码 |

### 业务服务

| 服务 | 说明 |
|------|------|
| **邮件服务** | 异步邮件发送，支持 HTML 模板、附件，内置欢迎邮件、密码重置等模板 |
| **文件服务** | 文件上传、存储和管理，支持类型验证、大小限制 |
| **缓存服务** | Redis 缓存封装，支持装饰器缓存、分布式锁 |
| **审计服务** | 操作日志记录，用于安全审计和问题追踪 |

### 异常处理

| 功能 | 说明 |
|------|------|
| **全局异常处理器** | 统一的错误响应格式，自动记录错误日志 |
| **自定义异常类** | 认证异常、授权异常、业务异常、验证异常等 |

### 事件系统

| 功能 | 说明 |
|------|------|
| **事件总线** | 发布/订阅模式，解耦业务逻辑 |
| **事件优先级** | 支持事件处理优先级控制 |
| **事件中间件** | 可扩展的事件处理链 |

### 工具集

| 工具 | 说明 |
|------|------|
| **分页工具** | 统一的偏移分页和游标分页 |
| **验证器** | 邮箱、手机号、身份证、密码强度验证 |
| **结构化日志** | JSON 格式日志，支持请求上下文 |

### 中间件

| 中间件 | 说明 |
|------|------|
| **请求日志** | 记录每个请求的详细信息 |
| **CORS** | 跨域资源共享配置 |
| **限流** | 基于 IP 的请求限流 |
| **请求 ID** | 为每个请求生成唯一标识 |

### 可选功能

{%- if cookiecutter.include_websocket == "yes" %}
- **WebSocket** - 实时通信支持，连接管理、房间、广播
{%- endif %}
{%- if cookiecutter.include_jinja2 == "yes" %}
- **Jinja2 模板** - 服务端渲染支持
{%- endif %}
{%- if cookiecutter.use_redis == "yes" %}
- **Redis** - 缓存、会话存储、分布式锁
{%- endif %}
{%- if cookiecutter.use_celery == "yes" %}
- **Celery** - 分布式任务队列
- **定时任务** - Celery Beat 调度
{%- endif %}
- **Docker** - 容器化部署，多阶段构建
- **测试** - Pytest 异步测试支持

## 项目结构

```
{{ cookiecutter.project_slug }}/
├── app/
│   ├── api/                    # API 路由
│   │   ├── v1/                 # API 版本 1
│   │   │   ├── endpoints/      # 路由处理器
│   │   │   └── router.py       # 路由聚合
│   │   └── deps.py             # 依赖注入
│   ├── core/                   # 核心模块
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # JWT 和加密
│   │   ├── rbac.py             # RBAC 实现
│   │   ├── exceptions.py       # 自定义异常
│   │   ├── exception_handlers.py  # 异常处理器
│   │   ├── events.py           # 事件系统
│   │   └── celery_app.py       # Celery 配置
│   ├── db/                     # 数据库
│   │   ├── base.py             # 基础模型
│   │   ├── session.py          # 会话管理
│   │   └── repositories/       # 仓储模式
│   ├── models/                 # SQLAlchemy 模型
│   ├── schemas/                # Pydantic 模式
│   ├── services/               # 业务逻辑
│   │   ├── user.py             # 用户服务
│   │   ├── auth.py             # 认证服务
│   │   ├── email.py            # 邮件服务
│   │   ├── file.py             # 文件服务
│   │   ├── cache.py            # 缓存服务
│   │   └── audit.py            # 审计服务
│   ├── tasks/                  # Celery 任务
│   ├── middleware/             # 自定义中间件
│   ├── utils/                  # 工具函数
│   │   ├── validators.py       # 数据验证器
│   │   ├── pagination.py       # 分页工具
│   │   └── logging.py          # 日志工具
│   └── main.py                 # 应用入口
├── tests/                      # 测试套件
│   ├── api/                    # API 测试
│   └── unit/                   # 单元测试
├── alembic/                    # 数据库迁移
├── docker/                     # Docker 配置
├── docker-compose.yml          # 生产环境
├── docker-compose.dev.yml      # 开发环境
├── requirements.txt            # 依赖包
└── .env.example                # 环境变量模板
```

## 快速开始

### 环境要求

- Python {{ cookiecutter.python_version }}+
- PostgreSQL / MySQL / SQLite
{%- if cookiecutter.use_redis == "yes" %}
- Redis
{%- endif %}

### 安装步骤

1. 创建虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件配置您的设置
```

4. 运行数据库迁移：
```bash
alembic upgrade head
```

5. 启动服务器：
```bash
uvicorn app.main:app --reload
```

### 使用 Docker

开发环境：
```bash
docker-compose -f docker-compose.dev.yml up --build
```

生产环境：
```bash
docker-compose up --build -d
```

## API 文档

启动服务后，可以通过以下地址访问 API 文档：

| 文档 | 地址 | 说明 |
|------|------|------|
| Swagger UI | http://localhost:8000/docs | 交互式 API 文档 |
| ReDoc | http://localhost:8000/redoc | 美观的 API 文档 |
| OpenAPI JSON | http://localhost:8000/openapi.json | OpenAPI 规范文件 |

---

## 配置说明

### 环境变量

复制 `.env.example` 为 `.env` 并根据实际情况修改：

#### 应用配置
```ini
# 应用名称
APP_NAME="{{ cookiecutter.project_name }}"
# 版本号
APP_VERSION="{{ cookiecutter.version }}"
# 运行环境：development, staging, production
ENVIRONMENT=development
# 调试模式
DEBUG=true
```

#### 安全配置
```ini
# JWT 密钥（生产环境必须修改）
SECRET_KEY=your-super-secret-key
# JWT 算法
JWT_ALGORITHM=HS256
# 访问令牌过期时间（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES=30
# 刷新令牌过期时间（天）
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### 数据库配置
```ini
# 数据库类型：postgresql, mysql, sqlite
DATABASE_TYPE=postgresql
# 数据库主机
DATABASE_HOST=localhost
# 数据库端口
DATABASE_PORT=5432
# 数据库用户名
DATABASE_USER=postgres
# 数据库密码
DATABASE_PASSWORD=postgres
# 数据库名
DATABASE_NAME={{ cookiecutter.project_slug }}
# 是否输出 SQL 语句
DATABASE_ECHO=false
```

{%- if cookiecutter.use_redis == "yes" %}
#### Redis 配置
```ini
# Redis 主机
REDIS_HOST=localhost
# Redis 端口
REDIS_PORT=6379
# Redis 数据库索引
REDIS_DB=0
# Redis 密码（可选）
REDIS_PASSWORD=
```
{%- endif %}

{%- if cookiecutter.use_celery == "yes" %}
#### Celery 配置
```ini
# Celery 消息代理
CELERY_BROKER_URL=redis://localhost:6379/0
# Celery 结果后端
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```
{%- endif %}

#### 邮件配置
```ini
# SMTP 服务器
SMTP_HOST=smtp.example.com
# SMTP 端口
SMTP_PORT=587
# SMTP 用户名
SMTP_USER=
# SMTP 密码
SMTP_PASSWORD=
# 发件人邮箱
FROM_EMAIL=noreply@example.com
# 发件人名称
FROM_NAME={{ cookiecutter.project_name }}
```

#### 限流配置
```ini
# 是否启用限流
RATE_LIMIT_ENABLED=true
# 请求数限制
RATE_LIMIT_REQUESTS=100
# 时间窗口（秒）
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## API 接口

### 接口概览

| 模块 | 前缀 | 说明 |
|------|------|------|
| 认证 | `/api/v1/auth` | 登录、注册、令牌刷新 |
| 用户 | `/api/v1/users` | 用户管理 CRUD |
| 角色 | `/api/v1/roles` | 角色管理 CRUD |
| 文件 | `/api/v1/files` | 文件上传和管理 |
| 健康 | `/api/v1/health` | 健康检查 |

### 认证接口

#### 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@example.com&password=your_password
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "newuser",
  "password": "SecurePassword123"
}
```

#### 刷新令牌
```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

### 用户接口

#### 获取当前用户信息
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

#### 获取用户列表（需要管理权限）
```http
GET /api/v1/users?page=1&page_size=20
Authorization: Bearer <access_token>
```

#### 创建用户（需要管理权限）
```http
POST /api/v1/users
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "SecurePassword123",
  "is_active": true
}
```

### 文件接口

#### 上传文件
```http
POST /api/v1/files/upload
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=@/path/to/file.jpg
```

#### 上传图片
```http
POST /api/v1/files/upload/image
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=@/path/to/image.jpg
```

### 健康检查

#### 应用健康状态
```http
GET /api/v1/health
```

响应：
```json
{
  "status": "healthy",
  "version": "{{ cookiecutter.version }}",
  "environment": "development",
  "database": "connected"
}
```

---

## 认证与授权

### RBAC 权限系统

项目采用基于角色的访问控制（RBAC）进行权限管理。

#### 预定义角色

| 角色 | 说明 |
|------|------|
| `superuser` | 超级管理员，拥有所有权限 |
| `admin` | 管理员，可管理用户和角色 |
| `user` | 普通用户，基本操作权限 |

#### 权限定义

```python
from app.core.rbac import Permission

# 用户权限
Permission.USER_READ      # 查看用户
Permission.USER_CREATE    # 创建用户
Permission.USER_UPDATE    # 更新用户
Permission.USER_DELETE    # 删除用户

# 角色权限
Permission.ROLE_READ      # 查看角色
Permission.ROLE_CREATE    # 创建角色
Permission.ROLE_UPDATE    # 更新角色
Permission.ROLE_DELETE    # 删除角色
```

#### 使用权限依赖

```python
from fastapi import APIRouter, Depends
from app.core.rbac import require_permissions, Permission

router = APIRouter()

@router.get("/admin/users")
async def list_users(
    _: None = Depends(require_permissions(Permission.USER_READ)),
):
    """只有拥有 USER_READ 权限的用户才能访问。"""
    pass
```

---

## 服务层使用指南

### 邮件服务

```python
from app.services.email import email_service, EmailTemplates

# 发送简单邮件
await email_service.send_simple(
    to="user@example.com",
    subject="测试邮件",
    body="这是一封测试邮件",
)

# 使用预定义模板发送欢迎邮件
subject, body, html_body = EmailTemplates.welcome_email(
    username="张三",
    login_url="https://example.com/login",
)
await email_service.send_simple(
    to="user@example.com",
    subject=subject,
    body=body,
    html_body=html_body,
)

# 发送密码重置邮件
subject, body, html_body = EmailTemplates.password_reset_email(
    username="张三",
    reset_url="https://example.com/reset?token=xxx",
    expires_in=30,  # 分钟
)
```

### 文件服务

```python
from fastapi import UploadFile
from app.services.file import file_service

# 上传文件
file_info = await file_service.upload(
    file=upload_file,
    folder="documents",
    max_size=10 * 1024 * 1024,  # 10MB
)
print(f"文件 URL: {file_info.url}")

# 上传图片（自动验证类型）
file_info = await file_service.upload_image(
    file=image_file,
    folder="avatars",
)

# 删除文件
await file_service.delete(file_info.filepath)
```

### 缓存服务

```python
from app.services.cache import cache_service, cached

# 基本缓存操作
await cache_service.set("key", "value", expire=300)  # 5分钟过期
value = await cache_service.get("key")
await cache_service.delete("key")

# 使用缓存装饰器
@cached(expire=60, prefix="user")
async def get_user_data(user_id: int):
    """结果会被缓存 60 秒。"""
    return await fetch_user_from_db(user_id)

# 分布式锁
token = await cache_service.acquire_lock("my_lock", timeout=10)
if token:
    try:
        # 执行需要互斥的操作
        pass
    finally:
        await cache_service.release_lock("my_lock", token)
```

### 审计服务

```python
from app.services.audit import audit_service, AuditAction

# 记录操作日志
await audit_service.log(
    db=db,
    action=AuditAction.USER_UPDATE,
    resource_type="user",
    resource_id=str(user_id),
    description="更新用户信息",
    old_value={"name": "旧名字"},
    new_value={"name": "新名字"},
    user=current_user,
    request=request,
)

# 查询审计日志
logs = await audit_service.get_logs(
    db=db,
    user_id=user_id,
    resource_type="user",
    limit=50,
)
```

### 事件系统

```python
from app.core.events import event_bus, on_event, UserCreatedEvent

# 订阅事件
@on_event(UserCreatedEvent)
async def handle_user_created(event: UserCreatedEvent):
    """处理用户创建事件。"""
    print(f"新用户创建: {event.username}")
    # 发送欢迎邮件等

# 发布事件
await event_bus.publish(UserCreatedEvent(
    user_id=user.id,
    email=user.email,
    username=user.username,
))
```

---

## 数据库操作

### 仓储模式

项目使用仓储模式封装数据库操作，提供类型安全的 CRUD 操作。

```python
from app.db.repositories.base import BaseRepository
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """用户仓储类。"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """通过邮箱查找用户。"""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

# 使用仓储
user_repo = UserRepository(db)

# 创建
user = await user_repo.create(user_create_schema)

# 查询
user = await user_repo.get(user_id)
users = await user_repo.get_multi(skip=0, limit=10)

# 更新
user = await user_repo.update(user_id, user_update_schema)

# 删除
await user_repo.delete(user_id)
```

### 数据库迁移

```bash
# 创建新的迁移文件
alembic revision --autogenerate -m "添加用户表字段"

# 应用所有迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade abc123

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

# 初始化数据
``` bash
python scripts/init_db.py
``` 

---

## 测试

### 运行测试

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/api/test_users.py

# 运行特定测试函数
pytest tests/api/test_users.py::test_get_user

# 显示详细输出
pytest -v

# 显示打印输出
pytest -s
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看覆盖率摘要
pytest --cov=app --cov-report=term-missing

# 报告输出到 htmlcov/ 目录
```

### 测试示例

```python
import pytest
from httpx import AsyncClient

class TestUserAPI:
    """用户 API 测试。"""
    
    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """测试获取当前用户信息。"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data["data"]
```

---

## 部署

### Docker 部署

#### 开发环境

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up --build

# 后台运行
docker-compose -f docker-compose.dev.yml up -d

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f app

# 停止
docker-compose -f docker-compose.dev.yml down
```

#### 生产环境

```bash
# 构建并启动
docker-compose up --build -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart app

# 停止并清理
docker-compose down -v
```

{%- if cookiecutter.use_celery == "yes" %}
### Celery 工作进程

```bash
# 启动 Worker
celery -A app.core.celery_app worker --loglevel=info

# 启动 Beat（定时任务调度）
celery -A app.core.celery_app beat --loglevel=info

# 同时启动 Worker 和 Beat
celery -A app.core.celery_app worker --beat --loglevel=info

# 查看活动任务
celery -A app.core.celery_app inspect active
```
{%- endif %}

### 生产环境清单

- [ ] 修改 `SECRET_KEY` 为安全的随机字符串
- [ ] 设置 `ENVIRONMENT=production`
- [ ] 设置 `DEBUG=false`
- [ ] 配置正式的数据库连接
- [ ] 配置 HTTPS
- [ ] 配置日志轮转
- [ ] 设置适当的 CORS 来源
- [ ] 配置监控和告警

---

## 开发规范

### 代码风格

项目使用以下工具保持代码质量：

```bash
# 代码格式化
black app tests

# 导入排序
isort app tests

# 类型检查
mypy app

# 代码检查
flake8 app tests
```

### 提交规范

推荐使用约定式提交：

```
<类型>(<范围>): <描述>

[正文]

[贴脚]
```

类型：
- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

### 目录结构说明

| 目录 | 说明 |
|------|------|
| `app/api/` | API 路由和端点处理器 |
| `app/core/` | 核心配置、安全、异常等 |
| `app/db/` | 数据库连接和仓储模式 |
| `app/models/` | SQLAlchemy ORM 模型 |
| `app/schemas/` | Pydantic 请求/响应模式 |
| `app/services/` | 业务逻辑服务层 |
| `app/middleware/` | 自定义中间件 |
| `app/utils/` | 工具函数和辅助类 |
| `app/tasks/` | Celery 异步任务 |
| `tests/` | 测试用例 |
| `alembic/` | 数据库迁移文件 |

---

## 常见问题

### Q: 如何添加新的 API 端点？

1. 在 `app/api/v1/endpoints/` 下创建新文件
2. 定义路由和处理函数
3. 在 `app/api/v1/router.py` 中注册路由

### Q: 如何添加新的数据库模型？

1. 在 `app/models/` 下创建模型文件
2. 在 `app/models/__init__.py` 中导出
3. 创建对应的 Pydantic schema
4. 运行 `alembic revision --autogenerate`
5. 运行 `alembic upgrade head`

### Q: 如何自定义异常？

```python
from app.core.exceptions import AppException

class MyCustomError(AppException):
    def __init__(self, message: str = "自定义错误"):
        super().__init__(
            message=message,
            error_code="MY_CUSTOM_ERROR",
            status_code=400,
        )
```

### Q: 如何添加定时任务？

1. 在 `app/tasks/` 下创建任务文件
2. 在 `app/core/celery_app.py` 的 `beat_schedule` 中注册

---

## 许可证

MIT 许可证

## 作者

{{ cookiecutter.author_name }} <{{ cookiecutter.author_email }}>
