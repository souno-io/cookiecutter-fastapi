# 数据库模块 (Database)

本模块提供数据库连接管理、ORM 基类和仓储模式实现。

## 目录

- [模块结构](#模块结构)
- [数据库会话管理](#数据库会话管理)
- [ORM 基类](#orm-基类)
- [仓储模式](#仓储模式)
- [数据库迁移](#数据库迁移)
- [最佳实践](#最佳实践)

---

## 模块结构

```
db/
├── __init__.py          # 模块导出
├── base.py              # SQLAlchemy Base 声明
├── session.py           # 数据库会话管理
└── repositories/
    ├── __init__.py      # 仓储模块导出
    └── base.py          # 基础仓储类
```

---

## 数据库会话管理

### 文件：`session.py`

提供异步数据库会话管理，基于 SQLAlchemy 2.0 异步引擎。

### 核心组件

```python
from app.db import engine, async_session_maker, get_db, init_db

# engine: 异步数据库引擎
# async_session_maker: 异步会话工厂
# get_db: FastAPI 依赖注入函数
# init_db: 数据库初始化函数
```

### 在 FastAPI 中使用

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db

router = APIRouter()

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    """获取用户列表"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
```

### 手动管理会话

```python
from app.db import async_session_maker

async def some_background_task():
    """后台任务中使用数据库"""
    async with async_session_maker() as session:
        async with session.begin():
            # 执行数据库操作
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            # 修改数据
            user = users[0]
            user.name = "新名称"
            # 自动提交（session.begin() 上下文管理器）
```

### 数据库初始化

```python
from app.db import init_db

# 在应用启动时调用
async def startup():
    await init_db()
```

---

## ORM 基类

### 文件：`base.py`

定义所有模型的基类，提供通用字段和功能。

### Base 类

```python
from app.db import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    # 继承自 Base 的通用字段：
    # created_at: 创建时间（自动设置）
    # updated_at: 更新时间（自动更新）
```

### 通用字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 主键，自动递增 |
| `created_at` | DateTime | 创建时间，自动设置 |
| `updated_at` | DateTime | 更新时间，自动更新 |

### 模型定义示例

```python
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class Article(Base):
    """文章模型"""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    published = Column(Boolean, default=False)
    
    # 外键关联
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="articles")
    
    # 模型方法
    def publish(self):
        """发布文章"""
        self.published = True
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}')>"
```

---

## 仓储模式

### 文件：`repositories/base.py`

实现仓储模式（Repository Pattern），封装数据访问逻辑。

### BaseRepository 类

提供通用的 CRUD 操作，支持泛型类型提示。

```python
from typing import TypeVar, Generic, Type
from app.db.repositories import BaseRepository
from app.models import User

# 创建用户仓储
class UserRepository(BaseRepository[User]):
    """用户仓储"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    # 自定义查询方法
    async def get_by_email(self, email: str) -> User | None:
        """通过邮箱查询用户"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(self) -> list[User]:
        """获取所有活跃用户"""
        result = await self.db.execute(
            select(User).where(User.is_active == True)
        )
        return result.scalars().all()
```

### 基础 CRUD 方法

```python
from app.db.repositories import BaseRepository
from app.models import User

# 在服务层使用
class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = BaseRepository(User, db)
    
    async def create_user(self, data: dict) -> User:
        """创建用户"""
        return await self.repo.create(data)
    
    async def get_user(self, user_id: int) -> User | None:
        """获取单个用户"""
        return await self.repo.get(user_id)
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """获取用户列表"""
        return await self.repo.get_multi(skip=skip, limit=limit)
    
    async def update_user(
        self,
        user_id: int,
        data: dict
    ) -> User | None:
        """更新用户"""
        user = await self.repo.get(user_id)
        if user:
            return await self.repo.update(user, data)
        return None
    
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.repo.get(user_id)
        if user:
            await self.repo.delete(user)
            return True
        return False
```

### BaseRepository 方法列表

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get(id)` | id: int | Model \| None | 按 ID 获取单条记录 |
| `get_multi(skip, limit)` | skip: int, limit: int | list[Model] | 获取多条记录 |
| `create(obj_in)` | obj_in: dict \| Schema | Model | 创建记录 |
| `update(db_obj, obj_in)` | db_obj: Model, obj_in: dict | Model | 更新记录 |
| `delete(db_obj)` | db_obj: Model | None | 删除记录 |
| `count()` | - | int | 统计总数 |
| `exists(id)` | id: int | bool | 检查是否存在 |

### 条件查询

```python
from sqlalchemy import select, and_, or_

class UserRepository(BaseRepository[User]):
    
    async def search(
        self,
        keyword: str = None,
        is_active: bool = None,
        role_id: int = None
    ) -> list[User]:
        """复杂条件查询"""
        query = select(User)
        
        conditions = []
        if keyword:
            conditions.append(
                or_(
                    User.username.ilike(f"%{keyword}%"),
                    User.email.ilike(f"%{keyword}%")
                )
            )
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        if role_id:
            conditions.append(User.role_id == role_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalars().all()
```

---

## 数据库迁移

使用 Alembic 管理数据库迁移。

### 常用命令

```bash
# 创建新的迁移文件
alembic revision --autogenerate -m "添加用户表"

# 执行迁移
alembic upgrade head

# 回滚一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>

# 查看迁移历史
alembic history

# 查看当前版本
alembic current

# 查看待执行的迁移
alembic heads
```

### 迁移文件示例

```python
# alembic/versions/xxx_create_users_table.py

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(200), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email')
    op.drop_table('users')
```

---

## 最佳实践

### 1. 事务管理

```python
async def transfer_money(
    db: AsyncSession,
    from_account_id: int,
    to_account_id: int,
    amount: float
):
    """转账操作（事务示例）"""
    async with db.begin():  # 开启事务
        from_account = await db.get(Account, from_account_id)
        to_account = await db.get(Account, to_account_id)
        
        if from_account.balance < amount:
            raise BusinessError("余额不足")
        
        from_account.balance -= amount
        to_account.balance += amount
        
        # 事务自动提交，出错自动回滚
```

### 2. 批量操作

```python
async def bulk_create_users(
    db: AsyncSession,
    users_data: list[dict]
) -> list[User]:
    """批量创建用户"""
    users = [User(**data) for data in users_data]
    db.add_all(users)
    await db.commit()
    
    # 刷新获取自动生成的 ID
    for user in users:
        await db.refresh(user)
    
    return users
```

### 3. 预加载关联数据

```python
from sqlalchemy.orm import selectinload, joinedload

async def get_user_with_roles(
    db: AsyncSession,
    user_id: int
) -> User | None:
    """获取用户及其角色（预加载）"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))  # 预加载角色
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_articles_with_author(
    db: AsyncSession
) -> list[Article]:
    """获取文章及作者（JOIN 加载）"""
    result = await db.execute(
        select(Article)
        .options(joinedload(Article.author))
        .order_by(Article.created_at.desc())
    )
    return result.scalars().unique().all()
```

### 4. 分页查询

```python
from sqlalchemy import func

async def get_paginated_users(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20
) -> tuple[list[User], int]:
    """分页获取用户"""
    # 获取总数
    count_result = await db.execute(
        select(func.count()).select_from(User)
    )
    total = count_result.scalar()
    
    # 获取分页数据
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User)
        .offset(offset)
        .limit(per_page)
        .order_by(User.id)
    )
    users = result.scalars().all()
    
    return users, total
```

### 5. 软删除

```python
from sqlalchemy import Column, Boolean, DateTime

class SoftDeleteMixin:
    """软删除混入类"""
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

class User(Base, SoftDeleteMixin):
    """支持软删除的用户模型"""
    __tablename__ = "users"
    # ...

# 查询时排除已删除的记录
async def get_active_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).where(User.is_deleted == False)
    )
    return result.scalars().all()
```

---

## 注意事项

1. **异步操作**: 所有数据库操作必须使用 `await`
2. **会话生命周期**: 使用依赖注入或上下文管理器管理会话
3. **事务边界**: 明确事务边界，避免长事务
4. **N+1 问题**: 使用 `selectinload` 或 `joinedload` 预加载关联数据
5. **索引优化**: 为常用查询字段添加索引
6. **连接池**: 生产环境注意配置合适的连接池大小
