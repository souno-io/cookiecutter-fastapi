"""
CORS（跨源资源共享）中间件配置。
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    为 FastAPI 应用配置 CORS 中间件。
    
    参数：
        app: FastAPI 应用实例
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_allow_methods_list,
        allow_headers=settings.cors_allow_headers_list,
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
