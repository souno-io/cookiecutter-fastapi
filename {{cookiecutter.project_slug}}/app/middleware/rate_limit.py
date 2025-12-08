"""
速率限制中间件。

提供请求速率限制以防止滥用。
"""

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    简单的内存速率限制中间件。
    
    对于生产环境，建议使用基于 Redis 的速率限制
    以支持分布式部署。
    
    配置项：
    - RATE_LIMIT_REQUESTS: 每个时间窗口内的最大请求数
    - RATE_LIMIT_WINDOW_SECONDS: 时间窗口（秒）
    """
    
    def __init__(self, app, requests: int = None, window: int = None):
        super().__init__(app)
        self.requests = requests or settings.RATE_LIMIT_REQUESTS
        self.window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        self.clients: Dict[str, list] = defaultdict(list)
    
    def _get_client_id(self, request: Request) -> str:
        """获取唯一的客户端标识符。"""
        # 如果在代理后面，使用转发的 IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """移除当前时间窗口之外的请求。"""
        cutoff = current_time - self.window
        self.clients[client_id] = [
            timestamp for timestamp in self.clients[client_id]
            if timestamp > cutoff
        ]
    
    def _is_rate_limited(self, client_id: str) -> Tuple[bool, int]:
        """
        检查客户端是否被限速。
        
        返回：
            (是否被限制, 剩余请求数) 元组
        """
        current_time = time.time()
        self._clean_old_requests(client_id, current_time)
        
        request_count = len(self.clients[client_id])
        remaining = max(0, self.requests - request_count)
        
        if request_count >= self.requests:
            return True, 0
        
        return False, remaining
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 如果禁用了速率限制则跳过
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # 跳过健康检查端点
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        is_limited, remaining = self._is_rate_limited(client_id)
        
        if is_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试。",
                headers={
                    "Retry-After": str(self.window),
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + self.window),
                },
            )
        
        # 记录此请求
        self.clients[client_id].append(time.time())
        
        # 处理请求
        response = await call_next(request)
        
        # 添加速率限制响应头
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(
            int(time.time()) + self.window
        )
        
        return response


{%- if cookiecutter.use_redis == "yes" %}
class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于 Redis 的速率限制，用于分布式部署。
    
    需要 Redis 连接。
    """
    
    def __init__(
        self,
        app,
        redis_url: str = None,
        requests: int = None,
        window: int = None,
    ):
        super().__init__(app)
        import redis.asyncio as redis
        
        self.redis = redis.from_url(redis_url or settings.REDIS_URL)
        self.requests = requests or settings.RATE_LIMIT_REQUESTS
        self.window = window or settings.RATE_LIMIT_WINDOW_SECONDS
    
    def _get_client_id(self, request: Request) -> str:
        """获取唯一的客户端标识符。"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        key = f"rate_limit:{client_id}"
        
        # 获取当前计数
        current = await self.redis.get(key)
        
        if current is not None and int(current) >= self.requests:
            ttl = await self.redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试。",
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                },
            )
        
        # 增加计数器
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window)
        results = await pipe.execute()
        
        count = results[0]
        remaining = max(0, self.requests - count)
        
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
{%- endif %}
