"""
{{ cookiecutter.project_name }} - FastAPI Application

{{ cookiecutter.project_description }}
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
{%- if cookiecutter.include_jinja2 == "yes" %}
from fastapi.templating import Jinja2Templates
{%- endif %}

from app.core.config import settings
from app.core.exception_handlers import setup_exception_handlers
from app.api.v1.router import api_router
from app.middleware.cors import setup_cors
from app.middleware.logging import LoggingMiddleware, setup_logging
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.db.session import init_db, close_db
{%- if cookiecutter.include_websocket == "yes" %}
from app.websocket.handlers import router as websocket_router
{%- endif %}
{%- if cookiecutter.include_jinja2 == "yes" %}
from app.views import router as views_router
{%- endif %}


# 配置日志
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期处理器。
    
    处理启动和关闭事件。
    """
    # 启动
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # 初始化数据库（如果需要则创建表）
    if settings.ENVIRONMENT == "development":
        await init_db()
        logger.info("Database initialized")
    
    yield
    
    # 关闭
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")


def create_application() -> FastAPI:
    """
    应用程序工厂。
    
    创建并配置 FastAPI 应用程序。
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        openapi_url=settings.OPENAPI_URL if settings.DEBUG else None,
        docs_url=settings.DOCS_URL if settings.DEBUG else None,
        redoc_url=settings.REDOC_URL if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # 配置 CORS
    setup_cors(app)
    
    # 配置全局异常处理器
    setup_exception_handlers(app)
    
    # 添加中间件（顺序很重要 - 先添加的 = 最外层）
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
    
    # 包含 API 路由
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    {%- if cookiecutter.include_websocket == "yes" %}
    # 包含 WebSocket 路由
    app.include_router(websocket_router, tags=["WebSocket"])
    {%- endif %}
    
    # 挂载静态文件
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=static_path), name="static")
    
    {%- if cookiecutter.include_jinja2 == "yes" %}
    # 配置模板
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    
    # 注册视图路由
    app.include_router(views_router)
    
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def home(request: Request):
        """渲染主页。"""
        from app.views import get_current_user_from_cookie
        from app.db.session import get_db
        
        # 尝试获取当前用户
        current_user = None
        try:
            async for db in get_db():
                current_user = await get_current_user_from_cookie(request, db)
                break
        except Exception:
            pass
        
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "config": settings, "current_user": current_user},
        )
    {%- else %}
    @app.get("/", include_in_schema=False)
    async def home():
        """API 根端点。"""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": settings.DOCS_URL,
        }
    {%- endif %}
    
    return app


# 创建应用实例
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
