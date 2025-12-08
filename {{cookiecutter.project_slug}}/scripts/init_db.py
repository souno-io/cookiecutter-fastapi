#!/usr/bin/env python
"""
数据库初始化脚本。

用于创建初始超级用户和默认角色。

用法:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.security import security_manager
from app.db.session import async_session_maker
from app.models.user import User
from app.models.role import Role


async def create_default_roles() -> list[Role]:
    """创建默认角色。"""
    # 注意: permissions 字段是逗号分隔的字符串，不是列表
    default_roles = [
        {
            "name": "admin",
            "description": "管理员，可管理用户和角色",
            "permissions": "user:read,user:create,user:update,user:delete,role:read,role:create,role:update,role:delete",
        },
        {
            "name": "user",
            "description": "普通用户，基本操作权限",
            "permissions": "user:read",
        },
    ]
    
    created_roles = []
    
    async with async_session_maker() as session:
        for role_data in default_roles:
            # 检查角色是否已存在
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            role = result.scalar_one_or_none()
            
            if not role:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"],
                )
                session.add(role)
                await session.commit()
                await session.refresh(role)
                print(f"✓ 角色已创建: {role.name}")
                created_roles.append(role)
            else:
                print(f"- 角色已存在: {role.name}")
                created_roles.append(role)
    
    return created_roles


async def create_superuser() -> User | None:
    """创建初始超级用户。"""
    async with async_session_maker() as session:
        # 检查超级用户是否已存在
        result = await session.execute(
            select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=security_manager.hash_password(
                    settings.FIRST_SUPERUSER_PASSWORD
                ),
                full_name="管理员",
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✓ 超级用户已创建: {settings.FIRST_SUPERUSER_EMAIL}")
            return user
        else:
            print(f"- 超级用户已存在: {settings.FIRST_SUPERUSER_EMAIL}")
            return None


async def main():
    """主函数：初始化数据库数据。"""
    print("=" * 50)
    print("数据库初始化脚本")
    print("=" * 50)
    print()
    
    print("1. 创建默认角色...")
    await create_default_roles()
    print()
    
    print("2. 创建超级用户...")
    await create_superuser()
    print()
    
    print("=" * 50)
    print("初始化完成！")
    print()
    print("您现在可以使用以下账号登录：")
    print(f"  邮箱: {settings.FIRST_SUPERUSER_EMAIL}")
    print(f"  密码: {settings.FIRST_SUPERUSER_PASSWORD}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
