"""
服务层单元测试。

测试业务逻辑服务。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import UserService
from app.services.cache import cache_service


class TestUserService:
    """用户服务测试类。"""
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(
        self,
        db_session: AsyncSession,
        test_user_email: str,
    ):
        """测试通过邮箱获取用户。"""
        user = await UserService.get_by_email(db_session, test_user_email)
        
        assert user is not None
        assert user.email == test_user_email
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(
        self,
        db_session: AsyncSession,
    ):
        """测试获取不存在的用户。"""
        user = await UserService.get_by_email(db_session, "notexist@example.com")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_create_user(
        self,
        db_session: AsyncSession,
    ):
        """测试创建用户。"""
        from app.schemas.user import UserCreate
        
        user_data = UserCreate(
            email="servicetest@example.com",
            username="servicetest",
            password="TestPassword123",
        )
        
        user = await UserService.create(db_session, user_data)
        
        assert user is not None
        assert user.email == user_data.email
        assert user.username == user_data.username
        # 密码应该被哈希
        assert user.hashed_password != user_data.password
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self,
        db_session: AsyncSession,
        test_user_email: str,
        test_user_password: str,
    ):
        """测试用户认证成功。"""
        user = await UserService.authenticate(
            db_session,
            test_user_email,
            test_user_password,
        )
        
        assert user is not None
        assert user.email == test_user_email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self,
        db_session: AsyncSession,
        test_user_email: str,
    ):
        """测试错误密码认证。"""
        user = await UserService.authenticate(
            db_session,
            test_user_email,
            "wrongpassword",
        )
        
        assert user is None


class TestCacheService:
    """缓存服务测试类。"""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """测试设置和获取缓存。"""
        with patch.object(cache_service, '_redis') as mock_redis:
            mock_redis.get = AsyncMock(return_value="test_value")
            mock_redis.set = AsyncMock(return_value=True)
            
            # 设置缓存
            await cache_service.set("test_key", "test_value", expire=60)
            
            # 获取缓存
            value = await cache_service.get("test_key")
            
            assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_delete_cache(self):
        """测试删除缓存。"""
        with patch.object(cache_service, '_redis') as mock_redis:
            mock_redis.delete = AsyncMock(return_value=1)
            
            result = await cache_service.delete("test_key")
            
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        """测试缓存装饰器。"""
        from app.services.cache import cached
        
        call_count = 0
        
        @cached(expire=60, prefix="test")
        async def cached_function(arg1: str):
            nonlocal call_count
            call_count += 1
            return f"result_{arg1}"
        
        # 第一次调用
        with patch.object(cache_service, 'get', AsyncMock(return_value=None)):
            with patch.object(cache_service, 'set', AsyncMock(return_value=True)):
                result1 = await cached_function("test")
                assert result1 == "result_test"
                assert call_count == 1
