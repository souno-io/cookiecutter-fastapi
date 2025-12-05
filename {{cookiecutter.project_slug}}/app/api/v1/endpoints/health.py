"""
健康检查端点。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the application",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """
    执行健康检查。
    
    返回应用程序健康状态，包括：
    - 应用程序版本
    - 环境
    - 数据库连接状态
    """
    # 检查数据库连接
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    {%- if cookiecutter.use_redis == "yes" %}
    # 检查 Redis 连接
    redis_status = "connected"
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
    except Exception:
        redis_status = "disconnected"
    {%- endif %}
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        {%- if cookiecutter.use_redis == "yes" %}
        redis=redis_status,
        {%- endif %}
    )


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Check if the application is ready to receive traffic",
)
async def readiness_check() -> dict:
    """Kubernetes 就绪探针端点。"""
    return {"status": "ready"}


@router.get(
    "/live",
    summary="Liveness Check",
    description="Check if the application is alive",
)
async def liveness_check() -> dict:
    """Kubernetes 存活探针端点。"""
    return {"status": "alive"}
