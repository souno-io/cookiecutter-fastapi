"""
请求 ID 中间件，用于请求追踪。
"""

import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    为每个请求添加唯一请求 ID 的中间件。
    
    请求 ID 可用于：
    - 跨服务请求追踪
    - 日志关联
    - 调试
    
    ID 可通过以下方式获取：
    - request.state.request_id
    - X-Request-ID 响应头
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 检查是否存在请求 ID（来自上游代理）
        request_id = request.headers.get("X-Request-ID")
        
        # 如果未提供则生成新 ID
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # 存储到请求状态中
        request.state.request_id = request_id
        
        # 处理请求
        response = await call_next(request)
        
        # 添加到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response


def get_request_id(request: Request) -> Optional[str]:
    """
    从请求状态中获取请求 ID。
    
    参数：
        request: FastAPI 请求对象
        
    返回：
        请求 ID 字符串或 None
    """
    return getattr(request.state, "request_id", None)
