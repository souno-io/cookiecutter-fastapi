# 工具模块 (Utils)

本模块提供各种实用工具函数和辅助类。

## 目录

- [模块结构](#模块结构)
- [辅助函数](#辅助函数)
- [分页工具](#分页工具)
- [数据验证器](#数据验证器)
- [日志工具](#日志工具)
- [自定义工具](#自定义工具)

---

## 模块结构

```
utils/
├── __init__.py      # 模块导出
├── helpers.py       # 通用辅助函数
├── pagination.py    # 分页工具
├── validators.py    # 数据验证器
└── logging.py       # 日志配置
```

---

## 辅助函数

### 文件：`helpers.py`

提供常用的工具函数。

### 函数列表

```python
from app.utils import (
    generate_random_string,
    slugify,
    format_datetime,
    paginate,
)
```

### generate_random_string

生成随机字符串，用于验证码、令牌等。

```python
from app.utils import generate_random_string

# 生成8位随机字符串（字母+数字）
code = generate_random_string(8)
# 输出: "aB3xK9mN"

# 仅数字
code = generate_random_string(6, digits_only=True)
# 输出: "382719"

# 自定义字符集
code = generate_random_string(10, chars="ABCDEF0123456789")
# 输出: "A3B7E9D2CF"

# 生成 UUID 格式
uuid_str = generate_random_string(format="uuid")
# 输出: "550e8400-e29b-41d4-a716-446655440000"
```

### slugify

将文本转换为 URL 友好的别名。

```python
from app.utils import slugify

# 中文转拼音
slug = slugify("你好世界")
# 输出: "ni-hao-shi-jie"

# 英文处理
slug = slugify("Hello World!")
# 输出: "hello-world"

# 混合文本
slug = slugify("FastAPI 入门教程 2024")
# 输出: "fastapi-ru-men-jiao-cheng-2024"

# 自定义分隔符
slug = slugify("Hello World", separator="_")
# 输出: "hello_world"

# 限制长度
slug = slugify("这是一个很长的标题文字", max_length=20)
# 输出: "zhe-shi-yi-ge-hen-ch"
```

### format_datetime

格式化日期时间。

```python
from datetime import datetime
from app.utils import format_datetime

now = datetime.now()

# 默认格式
formatted = format_datetime(now)
# 输出: "2024-01-01 12:00:00"

# 自定义格式
formatted = format_datetime(now, "%Y年%m月%d日")
# 输出: "2024年01月01日"

# 相对时间
formatted = format_datetime(now, relative=True)
# 输出: "刚刚" / "5分钟前" / "2小时前" / "昨天" / "3天前"

# 时区转换
formatted = format_datetime(now, timezone="Asia/Shanghai")
# 输出: "2024-01-01 20:00:00"
```

### 其他辅助函数

```python
from app.utils.helpers import (
    mask_email,
    mask_phone,
    truncate_text,
    calculate_age,
    is_valid_json,
    deep_merge,
    flatten_dict,
)

# 邮箱脱敏
mask_email("user@example.com")
# 输出: "us***@example.com"

# 手机号脱敏
mask_phone("13812345678")
# 输出: "138****5678"

# 文本截断
truncate_text("这是一段很长的文字...", max_length=10)
# 输出: "这是一段很长..."

# 计算年龄
from datetime import date
calculate_age(date(1990, 1, 1))
# 输出: 34

# JSON 验证
is_valid_json('{"key": "value"}')
# 输出: True

# 深度合并字典
deep_merge(
    {"a": 1, "b": {"c": 2}},
    {"b": {"d": 3}, "e": 4}
)
# 输出: {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

# 扁平化字典
flatten_dict({"a": {"b": {"c": 1}}})
# 输出: {"a.b.c": 1}
```

---

## 分页工具

### 文件：`pagination.py`

提供标准分页和游标分页功能。

### PaginationParams

FastAPI 依赖注入的分页参数。

```python
from fastapi import Depends
from app.utils import PaginationParams

@router.get("/users")
async def list_users(
    pagination: PaginationParams = Depends()
):
    """
    pagination.page: 当前页码（从1开始）
    pagination.per_page: 每页数量（默认20，最大100）
    pagination.skip: 偏移量（自动计算）
    """
    users = await service.get_multi(
        skip=pagination.skip,
        limit=pagination.per_page
    )
    return users
```

### PaginatedResponse

分页响应模型。

```python
from app.utils import PaginatedResponse, create_paginated_response

@router.get("/articles", response_model=PaginatedResponse[ArticleResponse])
async def list_articles(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # 获取数据和总数
    articles = await article_repo.get_multi(
        skip=pagination.skip,
        limit=pagination.per_page
    )
    total = await article_repo.count()
    
    # 创建分页响应
    return create_paginated_response(
        items=articles,
        total=total,
        params=pagination
    )
```

### 响应格式

```json
{
    "data": [
        {"id": 1, "title": "文章1"},
        {"id": 2, "title": "文章2"}
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "pages": 5,
        "has_next": true,
        "has_prev": false
    }
}
```

### 游标分页

适用于大数据集的高性能分页。

```python
from app.utils import CursorPaginationParams, CursorPaginatedResponse

@router.get("/timeline", response_model=CursorPaginatedResponse[PostResponse])
async def get_timeline(
    cursor: CursorPaginationParams = Depends()
):
    """
    cursor.cursor: 游标值（上一页的最后一条记录ID）
    cursor.limit: 每页数量
    cursor.direction: 方向（next/prev）
    """
    posts = await post_repo.get_after_cursor(
        cursor=cursor.cursor,
        limit=cursor.limit
    )
    
    return CursorPaginatedResponse(
        data=posts,
        next_cursor=posts[-1].id if posts else None,
        has_more=len(posts) == cursor.limit
    )
```

### 游标分页响应格式

```json
{
    "data": [
        {"id": 101, "content": "..."},
        {"id": 102, "content": "..."}
    ],
    "next_cursor": "102",
    "has_more": true
}
```

---

## 数据验证器

### 文件：`validators.py`

提供常用的数据验证函数。

### 邮箱验证

```python
from app.utils import validate_email

# 验证邮箱格式
email = validate_email("user@example.com")
# 返回: "user@example.com"

# 无效邮箱抛出 ValueError
validate_email("invalid-email")
# 抛出: ValueError("邮箱格式不正确")
```

### 手机号验证

```python
from app.utils import validate_phone

# 中国手机号
phone = validate_phone("13812345678")
# 返回: "13812345678"

# 指定国家
phone = validate_phone("+1234567890", country="US")

# 无效手机号
validate_phone("12345")
# 抛出: ValueError("手机号格式不正确")
```

### 密码强度验证

```python
from app.utils import validate_password_strength

# 默认规则验证
password = validate_password_strength("Abc123!@#")
# 返回: "Abc123!@#"

# 自定义规则
password = validate_password_strength(
    "MyPassword123",
    min_length=10,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=False
)

# 密码太弱
validate_password_strength("123456")
# 抛出: ValueError("密码至少需要8个字符")
```

### 用户名验证

```python
from app.utils import validate_username

# 有效用户名
username = validate_username("john_doe123")
# 返回: "john_doe123"

# 规则：
# - 3-50个字符
# - 以字母开头
# - 只能包含字母、数字、下划线

validate_username("123abc")
# 抛出: ValueError("用户名必须以字母开头")
```

### 正则模式

```python
from app.utils.validators import Patterns

# 预定义正则模式
Patterns.EMAIL      # 邮箱
Patterns.PHONE_CN   # 中国手机号
Patterns.ID_CARD_CN # 中国身份证
Patterns.USERNAME   # 用户名
Patterns.URL        # URL
Patterns.IPV4       # IPv4 地址
Patterns.UUID       # UUID

# 使用示例
import re

if re.match(Patterns.EMAIL, email):
    print("有效邮箱")

if re.match(Patterns.PHONE_CN, phone):
    print("有效手机号")
```

### 在 Pydantic 中使用

```python
from pydantic import BaseModel, field_validator
from app.utils import validate_email, validate_phone, validate_password_strength

class UserCreate(BaseModel):
    email: str
    phone: str
    password: str
    
    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        return validate_email(v)
    
    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return validate_phone(v)
    
    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)
```

### 自定义验证器

```python
from app.utils.validators import create_validator

# 创建自定义验证器
validate_order_no = create_validator(
    pattern=r"^ORD\d{14}$",
    error_message="订单号格式不正确，应为ORD+14位数字"
)

# 使用
order_no = validate_order_no("ORD20240101000001")
# 返回: "ORD20240101000001"

validate_order_no("INVALID")
# 抛出: ValueError("订单号格式不正确，应为ORD+14位数字")
```

---

## 日志工具

### 文件：`logging.py`

配置结构化日志。

### 日志配置

```python
from app.utils.logging import setup_logging, get_logger

# 初始化日志配置
setup_logging(
    level="INFO",
    format="json",  # json / text
    output="stdout"  # stdout / file
)

# 获取日志器
logger = get_logger(__name__)

# 记录日志
logger.info("用户登录", user_id=1, ip="192.168.1.1")
logger.warning("登录失败", username="test", reason="密码错误")
logger.error("数据库连接失败", error=str(e), retry_count=3)
```

### 日志输出格式

**JSON 格式（生产环境）：**
```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "level": "INFO",
    "logger": "app.services.auth",
    "message": "用户登录",
    "user_id": 1,
    "ip": "192.168.1.1",
    "request_id": "abc123"
}
```

**文本格式（开发环境）：**
```
2024-01-01 12:00:00 [INFO] app.services.auth: 用户登录 user_id=1 ip=192.168.1.1
```

### 上下文日志

```python
from app.utils.logging import log_context

# 绑定上下文
with log_context(user_id=1, request_id="abc123"):
    logger.info("处理请求")  # 自动包含 user_id 和 request_id
    logger.info("请求完成")

# 在中间件中绑定
async def logging_middleware(request, call_next):
    with log_context(
        request_id=request.state.request_id,
        path=request.url.path
    ):
        return await call_next(request)
```

### 日志级别

```python
import logging

# 设置模块日志级别
logging.getLogger("app.services").setLevel(logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

---

## 自定义工具

### 添加新工具函数

```python
# utils/crypto.py
import hashlib
import hmac
from base64 import b64encode, b64decode

def md5_hash(text: str) -> str:
    """计算 MD5 哈希"""
    return hashlib.md5(text.encode()).hexdigest()

def sha256_hash(text: str) -> str:
    """计算 SHA256 哈希"""
    return hashlib.sha256(text.encode()).hexdigest()

def hmac_sign(message: str, secret: str) -> str:
    """HMAC 签名"""
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

def base64_encode(data: bytes) -> str:
    """Base64 编码"""
    return b64encode(data).decode()

def base64_decode(data: str) -> bytes:
    """Base64 解码"""
    return b64decode(data)
```

### 添加工具类

```python
# utils/retry.py
import asyncio
from functools import wraps
from typing import Type

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception]] = (Exception,)
):
    """
    重试装饰器
    
    参数:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 捕获的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator

# 使用示例
@retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
async def fetch_data(url: str):
    """带重试的数据获取"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 注册新工具

```python
# utils/__init__.py
from app.utils.crypto import md5_hash, sha256_hash, hmac_sign
from app.utils.retry import retry

__all__ = [
    # ... 其他导出
    "md5_hash",
    "sha256_hash",
    "hmac_sign",
    "retry",
]
```

---

## 注意事项

1. **纯函数**: 工具函数应尽量是无副作用的纯函数
2. **类型提示**: 所有函数应有完整的类型提示
3. **文档字符串**: 每个函数应有清晰的文档说明
4. **单元测试**: 工具函数应有完整的单元测试
5. **异常处理**: 验证函数应抛出有意义的异常信息
6. **性能考虑**: 避免在工具函数中进行 I/O 操作
7. **可复用性**: 工具函数应通用且易于复用
