# 测试模块 (Tests)

本模块提供项目的测试用例，包括 API 集成测试和单元测试。

## 目录

- [模块结构](#模块结构)
- [测试配置](#测试配置)
- [API 测试](#api-测试)
- [单元测试](#单元测试)
- [测试工具](#测试工具)
- [运行测试](#运行测试)
- [测试覆盖率](#测试覆盖率)

---

## 模块结构

```
tests/
├── __init__.py          # 测试模块初始化
├── conftest.py          # pytest 配置和共享 fixtures
├── api/                 # API 集成测试
│   ├── __init__.py
│   ├── test_auth.py     # 认证接口测试
│   ├── test_users.py    # 用户接口测试
│   └── test_health.py   # 健康检查测试
└── unit/                # 单元测试
    ├── __init__.py
    ├── test_services.py # 服务层测试
    └── test_validators.py # 验证器测试
```

---

## 测试配置

### 文件：`conftest.py`

配置测试环境和共享 fixtures。

### 基础 Fixtures

```python
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.core.config import settings
from app.models import User, Role
from app.core.security import SecurityManager

# 测试数据库 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试引擎
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """初始化测试数据库"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """获取测试数据库会话"""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """获取测试客户端"""
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
```

### 用户相关 Fixtures

```python
@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=SecurityManager.hash_password("testpass123"),
        full_name="测试用户",
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_superuser(db: AsyncSession) -> User:
    """创建测试超级管理员"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=SecurityManager.hash_password("adminpass123"),
        full_name="管理员",
        is_active=True,
        is_superuser=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def user_token(test_user: User) -> str:
    """获取用户访问令牌"""
    return SecurityManager.create_access_token(
        data={"sub": str(test_user.id)}
    )


@pytest.fixture
async def admin_token(test_superuser: User) -> str:
    """获取管理员访问令牌"""
    return SecurityManager.create_access_token(
        data={"sub": str(test_superuser.id)}
    )


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """用户认证头"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """管理员认证头"""
    return {"Authorization": f"Bearer {admin_token}"}
```

---

## API 测试

### 认证接口测试

```python
# tests/api/test_auth.py
import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """认证接口测试"""
    
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user
    ):
        """测试登录成功"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        test_user
    ):
        """测试密码错误"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self,
        client: AsyncClient
    ):
        """测试用户不存在"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "anypassword"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(
        self,
        client: AsyncClient,
        test_user
    ):
        """测试刷新令牌"""
        # 先登录获取 refresh_token
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # 使用 refresh_token 获取新令牌
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    @pytest.mark.asyncio
    async def test_get_current_user(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """测试获取当前用户信息"""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        client: AsyncClient
    ):
        """测试未认证访问"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
```

### 用户接口测试

```python
# tests/api/test_users.py
import pytest
from httpx import AsyncClient


class TestUserEndpoints:
    """用户接口测试"""
    
    @pytest.mark.asyncio
    async def test_list_users(
        self,
        client: AsyncClient,
        admin_headers,
        test_user
    ):
        """测试获取用户列表"""
        response = await client.get(
            "/api/v1/users/",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    @pytest.mark.asyncio
    async def test_get_user(
        self,
        client: AsyncClient,
        admin_headers,
        test_user
    ):
        """测试获取单个用户"""
        response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(
        self,
        client: AsyncClient,
        admin_headers
    ):
        """测试获取不存在的用户"""
        response = await client.get(
            "/api/v1/users/99999",
            headers=admin_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_user(
        self,
        client: AsyncClient,
        admin_headers
    ):
        """测试创建用户"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpass123",
            "full_name": "新用户"
        }
        
        response = await client.post(
            "/api/v1/users/",
            json=user_data,
            headers=admin_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data  # 密码不应返回
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self,
        client: AsyncClient,
        admin_headers,
        test_user
    ):
        """测试创建重复用户名"""
        user_data = {
            "username": "testuser",  # 已存在
            "email": "another@example.com",
            "password": "password123"
        }
        
        response = await client.post(
            "/api/v1/users/",
            json=user_data,
            headers=admin_headers
        )
        
        assert response.status_code == 409
        assert "已存在" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_user(
        self,
        client: AsyncClient,
        admin_headers,
        test_user
    ):
        """测试更新用户"""
        update_data = {
            "full_name": "更新后的名称"
        }
        
        response = await client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert response.json()["full_name"] == "更新后的名称"
    
    @pytest.mark.asyncio
    async def test_delete_user(
        self,
        client: AsyncClient,
        admin_headers,
        db
    ):
        """测试删除用户"""
        # 创建要删除的用户
        from app.models import User
        from app.core.security import SecurityManager
        
        user = User(
            username="todelete",
            email="delete@example.com",
            hashed_password=SecurityManager.hash_password("pass123")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        response = await client.delete(
            f"/api/v1/users/{user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_permission_denied(
        self,
        client: AsyncClient,
        auth_headers  # 普通用户
    ):
        """测试权限不足"""
        response = await client.get(
            "/api/v1/users/",
            headers=auth_headers
        )
        
        # 普通用户无权访问用户列表
        assert response.status_code == 403
```

### 健康检查测试

```python
# tests/api/test_health.py
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查接口"""
        response = await client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """测试就绪检查"""
        response = await client.get("/api/v1/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
    
    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """测试存活检查"""
        response = await client.get("/api/v1/health/live")
        
        assert response.status_code == 200
```

---

## 单元测试

### 服务层测试

```python
# tests/unit/test_services.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import UserService, AuthService
from app.models import User
from app.schemas import UserCreate


class TestUserService:
    """用户服务测试"""
    
    @pytest.fixture
    def user_service(self, db: AsyncSession):
        return UserService(db)
    
    @pytest.mark.asyncio
    async def test_create_user(
        self,
        user_service: UserService,
        db: AsyncSession
    ):
        """测试创建用户"""
        user_data = UserCreate(
            username="servicetest",
            email="service@example.com",
            password="password123"
        )
        
        user = await user_service.create(user_data)
        
        assert user.id is not None
        assert user.username == "servicetest"
        assert user.email == "service@example.com"
        # 密码应该被哈希
        assert user.hashed_password != "password123"
    
    @pytest.mark.asyncio
    async def test_get_by_email(
        self,
        user_service: UserService,
        test_user: User
    ):
        """测试通过邮箱查询用户"""
        user = await user_service.get_by_email("test@example.com")
        
        assert user is not None
        assert user.id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_by_email_not_found(
        self,
        user_service: UserService
    ):
        """测试查询不存在的邮箱"""
        user = await user_service.get_by_email("notfound@example.com")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_password(
        self,
        user_service: UserService,
        test_user: User
    ):
        """测试更新密码"""
        old_password_hash = test_user.hashed_password
        
        await user_service.update_password(test_user, "newpassword123")
        
        assert test_user.hashed_password != old_password_hash
        assert test_user.check_password("newpassword123")


class TestAuthService:
    """认证服务测试"""
    
    @pytest.fixture
    def auth_service(self, db: AsyncSession):
        return AuthService(db)
    
    @pytest.mark.asyncio
    async def test_authenticate_success(
        self,
        auth_service: AuthService,
        test_user: User
    ):
        """测试认证成功"""
        user = await auth_service.authenticate(
            "testuser",
            "testpass123"
        )
        
        assert user is not None
        assert user.id == test_user.id
    
    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(
        self,
        auth_service: AuthService,
        test_user: User
    ):
        """测试密码错误"""
        user = await auth_service.authenticate(
            "testuser",
            "wrongpassword"
        )
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(
        self,
        auth_service: AuthService
    ):
        """测试用户不存在"""
        user = await auth_service.authenticate(
            "nonexistent",
            "password"
        )
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_create_tokens(
        self,
        auth_service: AuthService,
        test_user: User
    ):
        """测试生成令牌"""
        tokens = auth_service.create_tokens(test_user)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
```

### 验证器测试

```python
# tests/unit/test_validators.py
import pytest
from app.utils.validators import (
    validate_email,
    validate_phone,
    validate_password_strength,
    validate_username,
)


class TestEmailValidator:
    """邮箱验证测试"""
    
    def test_valid_email(self):
        """测试有效邮箱"""
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("user.name@example.co.uk") == "user.name@example.co.uk"
    
    def test_invalid_email(self):
        """测试无效邮箱"""
        with pytest.raises(ValueError, match="邮箱格式"):
            validate_email("invalid-email")
        
        with pytest.raises(ValueError):
            validate_email("@example.com")
        
        with pytest.raises(ValueError):
            validate_email("user@")


class TestPhoneValidator:
    """手机号验证测试"""
    
    def test_valid_phone(self):
        """测试有效手机号"""
        assert validate_phone("13812345678") == "13812345678"
        assert validate_phone("15912345678") == "15912345678"
    
    def test_invalid_phone(self):
        """测试无效手机号"""
        with pytest.raises(ValueError, match="手机号"):
            validate_phone("12345678901")  # 非1开头
        
        with pytest.raises(ValueError):
            validate_phone("1381234567")  # 少一位
        
        with pytest.raises(ValueError):
            validate_phone("138123456789")  # 多一位


class TestPasswordValidator:
    """密码强度验证测试"""
    
    def test_valid_password(self):
        """测试有效密码"""
        result = validate_password_strength("Abc123!@#")
        assert result == "Abc123!@#"
    
    def test_password_too_short(self):
        """测试密码过短"""
        with pytest.raises(ValueError, match="至少"):
            validate_password_strength("Abc1!")
    
    def test_password_no_uppercase(self):
        """测试缺少大写字母"""
        with pytest.raises(ValueError, match="大写"):
            validate_password_strength("abc123!@#")
    
    def test_password_no_lowercase(self):
        """测试缺少小写字母"""
        with pytest.raises(ValueError, match="小写"):
            validate_password_strength("ABC123!@#")
    
    def test_password_no_digit(self):
        """测试缺少数字"""
        with pytest.raises(ValueError, match="数字"):
            validate_password_strength("Abcdefg!@#")


class TestUsernameValidator:
    """用户名验证测试"""
    
    def test_valid_username(self):
        """测试有效用户名"""
        assert validate_username("john") == "john"
        assert validate_username("john_doe") == "john_doe"
        assert validate_username("john123") == "john123"
    
    def test_username_starts_with_number(self):
        """测试数字开头"""
        with pytest.raises(ValueError, match="字母开头"):
            validate_username("123john")
    
    def test_username_too_short(self):
        """测试用户名过短"""
        with pytest.raises(ValueError):
            validate_username("ab")
    
    def test_username_invalid_chars(self):
        """测试非法字符"""
        with pytest.raises(ValueError):
            validate_username("john-doe")  # 包含连字符
        
        with pytest.raises(ValueError):
            validate_username("john@doe")  # 包含@
```

---

## 测试工具

### Mock 和 Patch

```python
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_send_email_success():
    """测试发送邮件（Mock SMTP）"""
    with patch("app.services.email.smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        from app.services import email_service
        
        result = await email_service.send_simple(
            to="user@example.com",
            subject="测试",
            body="内容"
        )
        
        assert result is True
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_cache_service():
    """测试缓存服务（Mock Redis）"""
    with patch("app.services.cache.redis") as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        
        from app.services import cache_service
        
        # 测试缓存未命中
        result = await cache_service.get("key")
        assert result is None
        
        # 测试设置缓存
        result = await cache_service.set("key", "value")
        assert result is True
```

### 测试工厂

```python
# tests/factories.py
from datetime import datetime
from app.models import User, Role, Article
from app.core.security import SecurityManager


class UserFactory:
    """用户工厂"""
    
    @staticmethod
    def create(
        db,
        username: str = "testuser",
        email: str = "test@example.com",
        password: str = "password123",
        is_active: bool = True,
        is_superuser: bool = False,
        **kwargs
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=SecurityManager.hash_password(password),
            is_active=is_active,
            is_superuser=is_superuser,
            **kwargs
        )
        db.add(user)
        return user


class ArticleFactory:
    """文章工厂"""
    
    @staticmethod
    def create(
        db,
        title: str = "测试文章",
        content: str = "文章内容",
        author_id: int = 1,
        is_published: bool = False,
        **kwargs
    ) -> Article:
        article = Article(
            title=title,
            content=content,
            author_id=author_id,
            is_published=is_published,
            **kwargs
        )
        db.add(article)
        return article


# 使用工厂
@pytest.fixture
async def sample_users(db):
    """创建示例用户"""
    users = [
        UserFactory.create(db, username=f"user{i}", email=f"user{i}@example.com")
        for i in range(5)
    ]
    await db.commit()
    for user in users:
        await db.refresh(user)
    return users
```

---

## 运行测试

### 基本命令

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/api/test_auth.py

# 运行特定测试类
pytest tests/api/test_auth.py::TestAuthEndpoints

# 运行特定测试方法
pytest tests/api/test_auth.py::TestAuthEndpoints::test_login_success

# 显示详细输出
pytest -v

# 显示打印输出
pytest -s

# 失败时停止
pytest -x

# 只运行上次失败的测试
pytest --lf

# 并行运行
pytest -n 4
```

### 运行标记的测试

```python
# 标记测试
@pytest.mark.slow
async def test_slow_operation():
    ...

@pytest.mark.integration
async def test_integration():
    ...

# 运行特定标记
# pytest -m slow
# pytest -m "not slow"
# pytest -m "slow or integration"
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 安装 coverage
pip install pytest-cov

# 运行测试并生成覆盖率
pytest --cov=app --cov-report=html

# 指定最低覆盖率
pytest --cov=app --cov-fail-under=80

# 查看终端报告
pytest --cov=app --cov-report=term-missing
```

### 覆盖率配置

```ini
# pyproject.toml
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/migrations/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:"
]
```

---

## 注意事项

1. **测试隔离**: 每个测试应独立运行，不依赖其他测试
2. **数据库清理**: 使用事务回滚保持测试数据库清洁
3. **Mock 外部服务**: 避免在测试中调用真实的外部服务
4. **覆盖边界情况**: 测试正常流程和异常情况
5. **保持测试快速**: 单元测试应在毫秒级完成
6. **命名规范**: 测试方法名应清晰描述测试内容
7. **文档注释**: 复杂测试应添加说明注释
