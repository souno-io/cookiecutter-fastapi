"""
日志中间件，用于请求/响应日志记录。
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings


# 配置日志记录器
logger = logging.getLogger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求和响应日志中间件。
    
    记录内容：
    - 请求方法、路径和耗时
    - 响应状态码
    - 用于追踪的请求 ID
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 生成请求 ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取客户端信息
        client_host = request.client.host if request.client else "unknown"
        
        # 记录请求日志
        logger.info(
            f"Request started | "
            f"ID: {request_id} | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Client: {client_host}"
        )
        
        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            logger.error(
                f"Request failed | "
                f"ID: {request_id} | "
                f"Error: {str(e)} | "
                f"Duration: {process_time:.3f}s"
            )
            raise
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        # 记录响应日志
        logger.info(
            f"Request completed | "
            f"ID: {request_id} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time:.3f}s"
        )
        
        return response


def setup_logging() -> None:
    """配置应用程序日志。"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
        ],
    )
    
    # 如果配置了文件处理器则添加
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        logging.getLogger().addHandler(file_handler)
    
    # 减少第三方库的日志噪音
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
