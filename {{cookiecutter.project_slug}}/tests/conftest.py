"""
Pytest 配置和测试夹具。
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import security_manager
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User


# 测试数据库 URL（使用 SQLite 进行测试）
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# 测试会话工厂
test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """为测试会话创建默认事件循环实例。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """为每个测试创建新的数据库会话。"""
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with test_async_session_maker() as session:
        yield session
        await session.rollback()
    
    # 测试后删除所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建带有数据库会话覆盖的测试客户端。"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户。"""
    user = User(
        email="test@example.com",
        hashed_password=security_manager.hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_superuser(db_session: AsyncSession) -> User:
    """创建测试超级用户。"""
    user = User(
        email="admin@example.com",
        hashed_password=security_manager.hash_password("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_token(test_user: User) -> str:
    """为测试用户生成访问令牌。"""
    return security_manager.create_access_token(test_user.id)


@pytest_asyncio.fixture
async def superuser_token(test_superuser: User) -> str:
    """为测试超级用户生成访问令牌。"""
    return security_manager.create_access_token(test_superuser.id)


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """为普通用户生成授权头。"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def superuser_auth_headers(superuser_token: str) -> dict:
    """为超级用户生成授权头。"""
    return {"Authorization": f"Bearer {superuser_token}"}
