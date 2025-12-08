"""
健康检查端点测试。
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """测试健康检查端点返回健康状态。"""
    response = await client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """测试就绪检查端点。"""
    response = await client.get("/api/v1/health/ready")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_liveness_check(client: AsyncClient):
    """测试存活检查端点。"""
    response = await client.get("/api/v1/health/live")
    
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
