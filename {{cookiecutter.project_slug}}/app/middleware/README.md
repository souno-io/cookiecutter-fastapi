# 中间件模块 (Middleware)

本模块提供 HTTP 请求处理中间件，用于日志记录、跨域处理、请求限流等功能。

## 目录

- [模块结构](#模块结构)
- [日志中间件](#日志中间件)
- [CORS 中间件](#cors-中间件)
- [请求限流中间件](#请求限流中间件)
- [请求ID中间件](#请求id中间件)
- [自定义中间件](#自定义中间件)
- [中间件配置](#中间件配置)

---

## 模块结构

```
middleware/
├── __init__.py      # 模块导出
├── logging.py       # 日志记录中间件
├── cors.py          # 跨域资源共享配置
├── rate_limit.py    # 请求限流中间件
└── request_id.py    # 请求ID生成中间件
```

---

## 日志中间件

### 文件：`logging.py`

记录所有 HTTP 请求的详细信息。

### LoggingMiddleware 类

```python
from app.middleware import LoggingMiddleware

class LoggingMiddleware:
    """
    日志记录中间件
    
    记录内容：
    - 请求方法和路径
    - 请求参数和请求体
    - 响应状态码
    - 处理时间
    - 客户端IP
    - User-Agent
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: list[str] = None,  # 排除的路径
        log_request_body: bool = True,     # 是否记录请求体
        log_response_body: bool = False,   # 是否记录响应体
        max_body_length: int = 1000        # 最大记录长度
    ):
        ...
```

### 配置示例

```python
from fastapi import FastAPI
from app.middleware import LoggingMiddleware

app = FastAPI()

# 添加日志中间件
app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health", "/metrics", "/docs"],
    log_request_body=True,
    log_response_body=False
)
```

### 日志输出示例

```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "level": "INFO",
    "request_id": "abc123",
    "method": "POST",
    "path": "/api/v1/users",
    "query_params": {},
    "client_ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "status_code": 201,
    "duration_ms": 45.5,
    "user_id": 1
}
```

### 自定义日志格式

```python
import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

# 在中间件中使用
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger = structlog.get_logger()
        
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration, 2)
        )
        
        return response
```

---

## CORS 中间件

### 文件：`cors.py`

配置跨域资源共享（CORS）策略。

### setup_cors 函数

```python
from app.middleware import setup_cors

def setup_cors(app: FastAPI) -> None:
    """
    配置 CORS 中间件
    
    参数通过环境变量配置：
    - CORS_ORIGINS: 允许的源列表
    - CORS_ALLOW_CREDENTIALS: 是否允许携带凭证
    - CORS_ALLOW_METHODS: 允许的 HTTP 方法
    - CORS_ALLOW_HEADERS: 允许的请求头
    """
```

### 使用方式

```python
from fastapi import FastAPI
from app.middleware import setup_cors

app = FastAPI()

# 配置 CORS
setup_cors(app)
```

### 配置选项

```bash
# .env 文件

# 允许的源（逗号分隔）
CORS_ORIGINS=http://localhost:3000,https://example.com

# 允许携带凭证（Cookie）
CORS_ALLOW_CREDENTIALS=true

# 允许的 HTTP 方法
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS

# 允许的请求头
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Request-ID

# 预检请求缓存时间（秒）
CORS_MAX_AGE=600
```

### 自定义 CORS 配置

```python
from fastapi.middleware.cors import CORSMiddleware

# 开发环境：允许所有源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 生产环境：限制特定源
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.example.com",
        "https://admin.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
    max_age=600
)
```

---

## 请求限流中间件

### 文件：`rate_limit.py`

基于 IP 或用户的请求频率限制。

### RateLimitMiddleware 类

```python
from app.middleware import RateLimitMiddleware

class RateLimitMiddleware:
    """
    请求限流中间件
    
    支持多种限流策略：
    - 固定窗口（Fixed Window）
    - 滑动窗口（Sliding Window）
    - 令牌桶（Token Bucket）
    """
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limit: str = "100/minute",  # 限流规则
        key_func: Callable = None,        # 限流键生成函数
        exclude_paths: list[str] = None,  # 排除的路径
        storage: str = "redis"            # 存储后端
    ):
        ...
```

### 使用方式

```python
from fastapi import FastAPI
from app.middleware import RateLimitMiddleware

app = FastAPI()

# 全局限流：每分钟100次请求
app.add_middleware(
    RateLimitMiddleware,
    rate_limit="100/minute",
    exclude_paths=["/health", "/docs"]
)
```

### 限流规则格式

```python
# 支持的格式
"100/minute"     # 每分钟100次
"1000/hour"      # 每小时1000次
"10000/day"      # 每天10000次
"10/second"      # 每秒10次

# 多规则限流
rate_limits = [
    "10/second",     # 每秒最多10次
    "100/minute",    # 每分钟最多100次
    "1000/hour"      # 每小时最多1000次
]
```

### 自定义限流键

```python
from starlette.requests import Request

def get_rate_limit_key(request: Request) -> str:
    """自定义限流键"""
    # 基于用户ID限流（已登录用户）
    if hasattr(request.state, "user"):
        return f"user:{request.state.user.id}"
    
    # 基于 IP 限流（未登录用户）
    return f"ip:{request.client.host}"

app.add_middleware(
    RateLimitMiddleware,
    rate_limit="100/minute",
    key_func=get_rate_limit_key
)
```

### 路由级别限流

```python
from fastapi import Depends
from app.middleware.rate_limit import rate_limit

# 使用装饰器
@router.post("/login")
@rate_limit("5/minute")  # 登录接口：每分钟5次
async def login(credentials: LoginRequest):
    ...

# 使用依赖
@router.post("/send-sms")
async def send_sms(
    phone: str,
    _: None = Depends(rate_limit("1/minute"))  # 发送短信：每分钟1次
):
    ...
```

### 限流响应

```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "请求过于频繁，请稍后重试",
        "details": {
            "retry_after": 60
        }
    }
}
```

响应头：
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704067260
Retry-After: 60
```

---

## 请求ID中间件

### 文件：`request_id.py`

为每个请求生成唯一标识符，用于追踪和调试。

### RequestIDMiddleware 类

```python
from app.middleware import RequestIDMiddleware

class RequestIDMiddleware:
    """
    请求ID中间件
    
    功能：
    - 为每个请求生成唯一ID
    - 支持从请求头获取（前端传入）
    - 将ID添加到响应头
    - 注入到日志上下文
    """
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",  # 请求头名称
        generator: Callable = None           # ID生成函数
    ):
        ...
```

### 使用方式

```python
from fastapi import FastAPI, Request
from app.middleware import RequestIDMiddleware

app = FastAPI()

# 添加请求ID中间件
app.add_middleware(RequestIDMiddleware)

# 在路由中获取请求ID
@router.get("/")
async def index(request: Request):
    request_id = request.state.request_id
    return {"request_id": request_id}
```

### 自定义ID生成

```python
import uuid
import time

def generate_request_id() -> str:
    """生成请求ID：时间戳 + UUID 前8位"""
    timestamp = int(time.time() * 1000)
    unique = uuid.uuid4().hex[:8]
    return f"{timestamp}-{unique}"

app.add_middleware(
    RequestIDMiddleware,
    generator=generate_request_id
)
```

### 在日志中使用

```python
import structlog

# 配置 structlog 绑定请求ID
def add_request_id(logger, method_name, event_dict):
    from starlette.requests import Request
    request = event_dict.get("request")
    if request and hasattr(request.state, "request_id"):
        event_dict["request_id"] = request.state.request_id
    return event_dict

structlog.configure(
    processors=[
        add_request_id,
        structlog.processors.JSONRenderer()
    ]
)
```

---

## 自定义中间件

### 创建新中间件

```python
# middleware/authentication.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(
        self,
        app,
        exclude_paths: list[str] = None,
        auth_header: str = "Authorization"
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.auth_header = auth_header
    
    async def dispatch(
        self,
        request: Request,
        call_next
    ) -> Response:
        # 排除特定路径
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)
        
        # 获取认证令牌
        auth_header = request.headers.get(self.auth_header)
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                # 验证令牌
                payload = SecurityManager.verify_token(token)
                # 注入用户信息
                request.state.user_id = payload.get("sub")
                request.state.token_type = payload.get("type")
            except Exception:
                # 令牌无效，但不阻止请求
                pass
        
        return await call_next(request)
```

### 使用纯 ASGI 中间件

```python
# middleware/timing.py
from starlette.types import ASGIApp, Message, Receive, Scope, Send
import time

class TimingMiddleware:
    """请求耗时中间件（纯 ASGI 实现）"""
    
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.perf_counter()
        
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                # 计算耗时
                duration = time.perf_counter() - start_time
                # 添加响应头
                headers = list(message.get("headers", []))
                headers.append(
                    (b"X-Response-Time", f"{duration*1000:.2f}ms".encode())
                )
                message["headers"] = headers
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
```

### 注册中间件

```python
# middleware/__init__.py
from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.timing import TimingMiddleware

__all__ = [
    # ... 其他中间件
    "AuthenticationMiddleware",
    "TimingMiddleware",
]
```

---

## 中间件配置

### main.py 中配置

```python
from fastapi import FastAPI
from app.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    setup_cors,
)

app = FastAPI()

# 注意：中间件的添加顺序很重要
# 先添加的中间件在请求时最后执行，响应时最先执行

# 1. CORS（最外层）
setup_cors(app)

# 2. 请求ID
app.add_middleware(RequestIDMiddleware)

# 3. 日志记录
app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health", "/docs", "/openapi.json"]
)

# 4. 请求限流
app.add_middleware(
    RateLimitMiddleware,
    rate_limit="1000/hour",
    exclude_paths=["/health"]
)
```

### 中间件执行顺序

```
请求流程:
Client → CORS → RequestID → Logging → RateLimit → 路由处理

响应流程:
路由处理 → RateLimit → Logging → RequestID → CORS → Client
```

---

## 注意事项

1. **执行顺序**: 中间件按添加的相反顺序执行（LIFO）
2. **性能影响**: 避免在中间件中执行耗时操作
3. **异常处理**: 中间件中的异常应正确处理，避免请求挂起
4. **状态传递**: 使用 `request.state` 在中间件和路由间传递数据
5. **排除路径**: 为不需要处理的路径添加排除规则
6. **日志级别**: 生产环境注意调整日志级别，避免过多输出
7. **限流存储**: 生产环境使用 Redis 存储限流状态
