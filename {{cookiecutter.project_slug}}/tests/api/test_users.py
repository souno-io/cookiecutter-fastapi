"""
用户 API 测试。

测试用户相关的 API 端点。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token


class TestUserAPI:
    """用户 API 测试类。"""
    
    @pytest.mark.asyncio
    async def test_get_users_list(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """测试获取用户列表。"""
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_users_list_unauthorized(
        self,
        client: AsyncClient,
    ):
        """测试未授权访问用户列表。"""
        response = await client.get("/api/v1/users/")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """测试获取当前用户信息。"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "email" in data["data"]
    
    @pytest.mark.asyncio
    async def test_update_current_user(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """测试更新当前用户信息。"""
        update_data = {
            "username": "updated_user",
        }
        
        response = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"},
            json=update_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "updated_user"
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self,
        client: AsyncClient,
        admin_token: str,
        test_user_id: int,
    ):
        """测试根据 ID 获取用户。"""
        response = await client.get(
            f"/api/v1/users/{test_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_user_id
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """测试获取不存在的用户。"""
        response = await client.get(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_user(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        """测试创建用户。"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "NewPassword123",
        }
        
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=user_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["email"] == user_data["email"]
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self,
        client: AsyncClient,
        admin_token: str,
        test_user_email: str,
    ):
        """测试创建重复邮箱的用户。"""
        user_data = {
            "email": test_user_email,
            "username": "duplicateuser",
            "password": "Password123",
        }
        
        response = await client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=user_data,
        )
        
        assert response.status_code == 409
    
    @pytest.mark.asyncio
    async def test_delete_user(
        self,
        client: AsyncClient,
        admin_token: str,
        db_session: AsyncSession,
    ):
        """测试删除用户。"""
        # 先创建一个用户
        from app.models.user import User
        from app.core.security import get_password_hash
        
        user = User(
            email="todelete@example.com",
            username="todelete",
            hashed_password=get_password_hash("Password123"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 删除用户
        response = await client.delete(
            f"/api/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_change_password(
        self,
        client: AsyncClient,
        user_token: str,
    ):
        """测试修改密码。"""
        password_data = {
            "current_password": "TestPassword123",
            "new_password": "NewPassword456",
        }
        
        response = await client.post(
            "/api/v1/users/me/password",
            headers={"Authorization": f"Bearer {user_token}"},
            json=password_data,
        )
        
        # 根据实际 API 实现调整断言
        assert response.status_code in [200, 204]
