"""
Alembic 数据库迁移环境配置。
"""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import create_engine

from alembic import context

# 导入应用配置和模型
from app.core.config import settings
from app.db.base import Base

# 导入所有模型以便在 Base 中注册
from app.models import user, role, audit_log  # noqa: F401


# Alembic 配置对象
config = context.config

# 从应用配置设置 sqlalchemy.url
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

# 配置 Python 日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 自动生成支持的目标元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    在 'offline' 模式下运行迁移。

    此配置只使用 URL 而不是 Engine 来配置上下文，
    当然使用 Engine 也是可以的。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在 'online' 模式下运行迁移。

    创建 Engine 并将连接与上下文关联。
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
