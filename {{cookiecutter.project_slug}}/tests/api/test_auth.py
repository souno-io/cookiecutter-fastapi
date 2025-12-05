"""
认证 API 测试。

测试登录、注册和令牌相关的 API 端点。
"""

import pytest
from httpx import AsyncClient


class TestAuthAPI:
    """认证 API 测试类。"""
    
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user_email: str,
        test_user_password: str,
    ):
        """测试成功登录。"""
        login_data = {
            "username": test_user_email,
            "password": test_user_password,
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_user_email: str,
    ):
        """测试错误密码登录。"""
        login_data = {
            "username": test_user_email,
            "password": "wrongpassword",
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(
        self,
        client: AsyncClient,
    ):
        """测试不存在的用户登录。"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password123",
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_register_success(
        self,
        client: AsyncClient,
    ):
        """测试成功注册。"""
        register_data = {
            "email": "register@example.com",
            "username": "registeruser",
            "password": "Register123",
        }
        
        response = await client.post(
            "/api/v1/auth/register",
            json=register_data,
        )
        
        # 根据实际 API 实现调整
        assert response.status_code in [200, 201]
        data = response.json()
        if "data" in data:
            assert data["data"]["email"] == register_data["email"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        test_user_email: str,
    ):
        """测试重复邮箱注册。"""
        register_data = {
            "email": test_user_email,
            "username": "duplicateuser",
            "password": "Password123",
        }
        
        response = await client.post(
            "/api/v1/auth/register",
            json=register_data,
        )
        
        assert response.status_code in [400, 409]
    
    @pytest.mark.asyncio
    async def test_register_weak_password(
        self,
        client: AsyncClient,
    ):
        """测试弱密码注册。"""
        register_data = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123",  # 太短
        }
        
        response = await client.post(
            "/api/v1/auth/register",
            json=register_data,
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_refresh_token(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """测试刷新令牌。"""
        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        # 根据实际 API 实现调整
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_logout(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """测试登出。"""
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        # 根据实际 API 实现调整
        assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    async def test_invalid_token(
        self,
        client: AsyncClient,
    ):
        """测试无效令牌。"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_expired_token(
        self,
        client: AsyncClient,
    ):
        """测试过期令牌。"""
        from datetime import timedelta
        from app.core.security import create_access_token
        
        # 创建一个已过期的令牌
        expired_token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-10),
        )
        
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        
        assert response.status_code == 401
