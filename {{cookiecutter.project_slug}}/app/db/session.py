"""
数据库会话管理，支持异步操作。

提供：
- 异步 SQLAlchemy 引擎
- 会话工厂
- FastAPI 依赖注入
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    # SQLite 使用 NullPool，其他使用默认连接池
    poolclass=NullPool if "sqlite" in settings.DATABASE_URL else None,
)

# 会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    提供数据库会话的依赖项。
    
    用法:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库表。
    
    在生产环境中，请使用 Alembic 迁移。
    """
    from app.db.base import Base
    # 导入所有模型以确保它们在 Base 中注册
    from app.models import user, role  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接。"""
    await engine.dispose()
