# 核心模块 (Core)

本模块提供应用程序的核心功能，包括配置管理、安全认证、权限控制、异常处理和事件系统。

## 目录

- [模块结构](#模块结构)
- [配置管理](#配置管理)
- [安全认证](#安全认证)
- [RBAC 权限控制](#rbac-权限控制)
- [异常处理](#异常处理)
- [事件系统](#事件系统)
- [Celery 异步任务](#celery-异步任务)

---

## 模块结构

```
core/
├── __init__.py          # 模块导出
├── config.py            # 应用配置管理
├── security.py          # 安全功能（JWT、密码哈希）
├── rbac.py              # 基于角色的访问控制
├── exceptions.py        # 自定义异常类
├── exception_handlers.py # 全局异常处理器
├── events.py            # 事件发布/订阅系统
└── celery_app.py        # Celery 异步任务配置
```

---

## 配置管理

### 文件：`config.py`

使用 Pydantic Settings 从环境变量加载配置，支持类型验证和默认值。

### 使用方式

```python
from app.core.config import settings

# 访问配置项
print(settings.APP_NAME)
print(settings.DATABASE_URL)
print(settings.DEBUG)
```

### 主要配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `APP_NAME` | str | - | 应用名称 |
| `APP_VERSION` | str | "1.0.0" | 应用版本 |
| `DEBUG` | bool | False | 调试模式 |
| `ENVIRONMENT` | str | "development" | 运行环境 |
| `SECRET_KEY` | str | - | JWT 加密密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | 访问令牌过期时间（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | 7 | 刷新令牌过期时间（天） |
| `DATABASE_URL` | str | - | 数据库连接字符串 |
| `REDIS_URL` | str | - | Redis 连接字符串 |

### 环境变量示例

```bash
# .env 文件
APP_NAME=我的应用
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
DEBUG=true
```

---

## 安全认证

### 文件：`security.py`

提供 JWT 令牌生成/验证和密码哈希功能。

### SecurityManager 类

```python
from app.core.security import SecurityManager

# 创建访问令牌
token = SecurityManager.create_access_token(
    data={"sub": str(user_id)},
    expires_delta=timedelta(minutes=30)  # 可选
)

# 创建刷新令牌
refresh_token = SecurityManager.create_refresh_token(
    data={"sub": str(user_id)}
)

# 验证令牌
payload = SecurityManager.verify_token(token)
user_id = payload.get("sub")

# 密码哈希
hashed = SecurityManager.hash_password("plain_password")

# 验证密码
is_valid = SecurityManager.verify_password("plain_password", hashed)
```

### JWT 令牌结构

```json
{
    "sub": "用户ID",
    "exp": "过期时间戳",
    "iat": "签发时间戳",
    "type": "access/refresh"
}
```

---

## RBAC 权限控制

### 文件：`rbac.py`

实现基于角色的访问控制（Role-Based Access Control）。

### 权限定义

```python
from app.core.rbac import Permission

# 预定义权限
Permission.USER_CREATE    # 创建用户
Permission.USER_READ      # 读取用户
Permission.USER_UPDATE    # 更新用户
Permission.USER_DELETE    # 删除用户
Permission.ROLE_MANAGE    # 角色管理
Permission.SYSTEM_ADMIN   # 系统管理
```

### 在路由中使用

```python
from fastapi import APIRouter, Depends
from app.core.rbac import require_permissions, Permission

router = APIRouter()

# 单个权限检查
@router.get("/users")
async def list_users(
    _: None = Depends(require_permissions(Permission.USER_READ))
):
    return {"users": []}

# 多个权限检查（需要全部满足）
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    _: None = Depends(require_permissions(
        Permission.USER_DELETE,
        Permission.SYSTEM_ADMIN
    ))
):
    return {"message": "用户已删除"}
```

### RBACManager 类

```python
from app.core.rbac import RBACManager

rbac = RBACManager()

# 检查用户权限
has_permission = await rbac.check_permission(
    db=db,
    user_id=user_id,
    permission=Permission.USER_READ
)

# 获取用户所有权限
permissions = await rbac.get_user_permissions(db, user_id)

# 分配角色给用户
await rbac.assign_role(db, user_id, role_id)

# 移除用户角色
await rbac.remove_role(db, user_id, role_id)
```

### 预定义角色

| 角色 | 权限 | 说明 |
|------|------|------|
| `admin` | 全部权限 | 系统管理员 |
| `user` | USER_READ | 普通用户 |
| `moderator` | USER_READ, USER_UPDATE | 内容审核员 |

---

## 异常处理

### 文件：`exceptions.py`

定义应用专用异常类，统一错误响应格式。

### 异常类层级

```
AppException (基类)
├── AuthenticationError    # 认证错误 (401)
├── AuthorizationError     # 授权错误 (403)
├── NotFoundError          # 资源不存在 (404)
├── ValidationError        # 数据验证错误 (422)
├── ConflictError          # 资源冲突 (409)
├── RateLimitError         # 请求频率限制 (429)
├── BusinessError          # 业务逻辑错误 (400)
└── ExternalServiceError   # 外部服务错误 (502)
```

### 使用示例

```python
from app.core.exceptions import (
    NotFoundError,
    AuthenticationError,
    ValidationError,
    BusinessError,
)

# 资源不存在
raise NotFoundError(
    message="用户不存在",
    resource="user",
    resource_id=123
)

# 认证失败
raise AuthenticationError(
    message="无效的访问令牌"
)

# 数据验证错误
raise ValidationError(
    message="邮箱格式不正确",
    field="email",
    value="invalid-email"
)

# 业务逻辑错误
raise BusinessError(
    message="账户余额不足",
    error_code="INSUFFICIENT_BALANCE"
)
```

### 文件：`exception_handlers.py`

全局异常处理器，自动捕获异常并返回统一格式的 JSON 响应。

### 响应格式

```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "用户不存在",
        "details": {
            "resource": "user",
            "resource_id": 123
        }
    },
    "request_id": "uuid-string"
}
```

### 在 main.py 中配置

```python
from app.core.exception_handlers import setup_exception_handlers

app = FastAPI()
setup_exception_handlers(app)
```

---

## 事件系统

### 文件：`events.py`

实现事件驱动架构的发布/订阅模式。

### 定义事件

```python
from app.core.events import Event
from dataclasses import dataclass

@dataclass
class UserCreatedEvent(Event):
    """用户创建事件"""
    user_id: int
    email: str
    username: str

@dataclass
class OrderPaidEvent(Event):
    """订单支付事件"""
    order_id: int
    amount: float
    user_id: int
```

### 订阅事件

```python
from app.core.events import event_bus, on_event

# 使用装饰器订阅
@on_event(UserCreatedEvent)
async def send_welcome_email(event: UserCreatedEvent):
    """发送欢迎邮件"""
    await email_service.send_welcome(event.email, event.username)

@on_event(UserCreatedEvent, priority=10)  # 优先级越高越先执行
async def create_user_profile(event: UserCreatedEvent):
    """创建用户档案"""
    await profile_service.create(event.user_id)

# 手动订阅
event_bus.subscribe(
    event_type=OrderPaidEvent,
    handler=process_order,
    priority=5
)
```

### 发布事件

```python
from app.core.events import event_bus

# 发布事件
await event_bus.publish(
    UserCreatedEvent(
        user_id=1,
        email="user@example.com",
        username="新用户"
    )
)

# 带过滤器的事件发布
await event_bus.publish(
    OrderPaidEvent(order_id=100, amount=99.9, user_id=1)
)
```

### 事件过滤器

```python
# 只处理特定条件的事件
@on_event(
    OrderPaidEvent,
    filters={"amount": lambda x: x > 100}  # 只处理金额大于100的订单
)
async def handle_large_order(event: OrderPaidEvent):
    await notify_manager(event.order_id)
```

---

## Celery 异步任务

### 文件：`celery_app.py`

配置 Celery 分布式任务队列。

### 基本配置

```python
from app.core.celery_app import celery_app

# celery_app 已配置好 broker 和 backend
# broker: Redis
# backend: Redis
```

### 定义任务

```python
from app.core.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, to: str, subject: str, body: str):
    """发送邮件任务"""
    try:
        # 发送邮件逻辑
        pass
    except Exception as exc:
        # 重试，指数退避
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### 调用任务

```python
# 异步调用
send_email_task.delay("user@example.com", "标题", "内容")

# 延迟执行
send_email_task.apply_async(
    args=["user@example.com", "标题", "内容"],
    countdown=60  # 60秒后执行
)

# 定时执行
from datetime import datetime, timedelta
send_email_task.apply_async(
    args=["user@example.com", "标题", "内容"],
    eta=datetime.now() + timedelta(hours=1)  # 1小时后执行
)
```

### 定时任务配置

```python
# 在 celery_app.py 中配置
celery_app.conf.beat_schedule = {
    'cleanup-expired-tokens': {
        'task': 'app.tasks.maintenance.cleanup_expired_tokens',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    },
    'send-daily-report': {
        'task': 'app.tasks.email.send_daily_report',
        'schedule': crontab(hour=8, minute=0),  # 每天早上8点
    },
}
```

### 启动 Worker

```bash
# 启动 worker
celery -A app.core.celery_app worker --loglevel=info

# 启动 beat（定时任务调度器）
celery -A app.core.celery_app beat --loglevel=info

# 同时启动（开发环境）
celery -A app.core.celery_app worker --beat --loglevel=info
```

---

## 注意事项

1. **SECRET_KEY**: 生产环境必须使用强密钥，不要使用默认值
2. **敏感信息**: 所有敏感配置应通过环境变量传入，不要硬编码
3. **权限检查**: 所有需要授权的接口都应使用 `require_permissions` 装饰器
4. **异常处理**: 业务逻辑中应抛出自定义异常，由全局处理器统一处理
5. **事件解耦**: 使用事件系统解耦业务逻辑，提高代码可维护性
6. **异步任务**: 耗时操作（如发送邮件）应使用 Celery 异步执行
