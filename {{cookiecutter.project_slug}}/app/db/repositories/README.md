# 仓储模式模块 (Repositories)

本模块实现仓储模式（Repository Pattern），封装数据访问逻辑，提供统一的数据操作接口。

## 目录

- [设计理念](#设计理念)
- [基础仓储类](#基础仓储类)
- [使用方式](#使用方式)
- [自定义仓储](#自定义仓储)
- [高级查询](#高级查询)
- [最佳实践](#最佳实践)

---

## 设计理念

仓储模式的核心目标：

1. **解耦业务逻辑和数据访问**: 服务层不直接操作数据库
2. **统一数据访问接口**: 提供一致的 CRUD 操作
3. **便于测试**: 可以轻松 Mock 仓储进行单元测试
4. **代码复用**: 通用操作在基类中实现

```
┌─────────────────┐
│   API 端点      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   服务层        │  业务逻辑
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   仓储层        │  数据访问
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   数据库        │
└─────────────────┘
```

---

## 基础仓储类

### 文件：`base.py`

提供通用的 CRUD 操作基类。

### BaseRepository 类

```python
from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    基础仓储类
    
    提供通用的 CRUD 操作：
    - get: 按 ID 获取单条记录
    - get_multi: 获取多条记录
    - create: 创建记录
    - update: 更新记录
    - delete: 删除记录
    - count: 统计数量
    - exists: 检查是否存在
    """
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
```

### 方法详解

#### get - 获取单条记录

```python
async def get(self, id: int) -> Optional[ModelType]:
    """
    按 ID 获取单条记录
    
    参数:
        id: 主键 ID
    
    返回:
        模型实例或 None
    """
    result = await self.db.execute(
        select(self.model).where(self.model.id == id)
    )
    return result.scalar_one_or_none()
```

#### get_multi - 获取多条记录

```python
async def get_multi(
    self,
    skip: int = 0,
    limit: int = 100,
    order_by: str = None,
    desc: bool = True
) -> List[ModelType]:
    """
    获取多条记录（分页）
    
    参数:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        order_by: 排序字段
        desc: 是否降序
    
    返回:
        模型实例列表
    """
    query = select(self.model)
    
    if order_by:
        order_column = getattr(self.model, order_by)
        query = query.order_by(
            order_column.desc() if desc else order_column.asc()
        )
    
    query = query.offset(skip).limit(limit)
    result = await self.db.execute(query)
    return result.scalars().all()
```

#### create - 创建记录

```python
async def create(
    self,
    obj_in: CreateSchemaType | dict
) -> ModelType:
    """
    创建新记录
    
    参数:
        obj_in: Pydantic 模式或字典
    
    返回:
        创建的模型实例
    """
    if isinstance(obj_in, dict):
        create_data = obj_in
    else:
        create_data = obj_in.model_dump()
    
    db_obj = self.model(**create_data)
    self.db.add(db_obj)
    await self.db.commit()
    await self.db.refresh(db_obj)
    return db_obj
```

#### update - 更新记录

```python
async def update(
    self,
    db_obj: ModelType,
    obj_in: UpdateSchemaType | dict
) -> ModelType:
    """
    更新记录
    
    参数:
        db_obj: 要更新的模型实例
        obj_in: 更新数据
    
    返回:
        更新后的模型实例
    """
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(db_obj, field):
            setattr(db_obj, field, value)
    
    await self.db.commit()
    await self.db.refresh(db_obj)
    return db_obj
```

#### delete - 删除记录

```python
async def delete(self, db_obj: ModelType) -> None:
    """
    删除记录
    
    参数:
        db_obj: 要删除的模型实例
    """
    await self.db.delete(db_obj)
    await self.db.commit()
```

#### count - 统计数量

```python
async def count(self, **filters) -> int:
    """
    统计记录数量
    
    参数:
        **filters: 过滤条件
    
    返回:
        记录数量
    """
    query = select(func.count()).select_from(self.model)
    
    for key, value in filters.items():
        if hasattr(self.model, key):
            query = query.where(getattr(self.model, key) == value)
    
    result = await self.db.execute(query)
    return result.scalar()
```

#### exists - 检查是否存在

```python
async def exists(self, id: int) -> bool:
    """
    检查记录是否存在
    
    参数:
        id: 主键 ID
    
    返回:
        是否存在
    """
    result = await self.db.execute(
        select(self.model.id).where(self.model.id == id)
    )
    return result.scalar_one_or_none() is not None
```

---

## 使用方式

### 直接使用 BaseRepository

```python
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.db import get_db
from app.db.repositories import BaseRepository
from app.models import Article
from app.schemas import ArticleCreate, ArticleUpdate

@router.get("/articles")
async def list_articles(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    repo = BaseRepository(Article, db)
    articles = await repo.get_multi(skip=skip, limit=limit)
    return articles

@router.post("/articles")
async def create_article(
    article: ArticleCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = BaseRepository(Article, db)
    return await repo.create(article)

@router.get("/articles/{article_id}")
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = BaseRepository(Article, db)
    article = await repo.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article
```

### 通过服务层使用

```python
# services/article.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories import BaseRepository
from app.models import Article
from app.schemas import ArticleCreate, ArticleUpdate

class ArticleService:
    def __init__(self, db: AsyncSession):
        self.repo = BaseRepository(Article, db)
        self.db = db
    
    async def get_article(self, article_id: int) -> Article | None:
        return await self.repo.get(article_id)
    
    async def list_articles(
        self,
        skip: int = 0,
        limit: int = 20
    ) -> list[Article]:
        return await self.repo.get_multi(skip=skip, limit=limit)
    
    async def create_article(
        self,
        data: ArticleCreate,
        author_id: int
    ) -> Article:
        article_data = data.model_dump()
        article_data["author_id"] = author_id
        return await self.repo.create(article_data)
    
    async def update_article(
        self,
        article: Article,
        data: ArticleUpdate
    ) -> Article:
        return await self.repo.update(article, data)
    
    async def delete_article(self, article: Article) -> None:
        await self.repo.delete(article)
```

---

## 自定义仓储

### 创建专用仓储类

```python
# repositories/user.py
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.db.repositories import BaseRepository
from app.models import User
from app.schemas import UserCreate, UserUpdate

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """用户仓储"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_email(self, email: str) -> User | None:
        """通过邮箱查询用户"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> User | None:
        """通过用户名查询用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username_or_email(
        self,
        identifier: str
    ) -> User | None:
        """通过用户名或邮箱查询"""
        result = await self.db.execute(
            select(User).where(
                or_(
                    User.username == identifier,
                    User.email == identifier
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_with_roles(self, user_id: int) -> User | None:
        """获取用户及其角色"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """获取活跃用户列表"""
        result = await self.db.execute(
            select(User)
            .where(User.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def search(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 20
    ) -> list[User]:
        """搜索用户"""
        result = await self.db.execute(
            select(User)
            .where(
                or_(
                    User.username.ilike(f"%{keyword}%"),
                    User.email.ilike(f"%{keyword}%"),
                    User.full_name.ilike(f"%{keyword}%")
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
```

### 使用自定义仓储

```python
from app.repositories import UserRepository

class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)
    
    async def authenticate(
        self,
        identifier: str,
        password: str
    ) -> User | None:
        user = await self.repo.get_by_username_or_email(identifier)
        if user and user.check_password(password):
            return user
        return None
    
    async def get_user_with_permissions(
        self,
        user_id: int
    ) -> User | None:
        return await self.repo.get_with_roles(user_id)
```

---

## 高级查询

### 条件查询

```python
class ArticleRepository(BaseRepository[Article, ArticleCreate, ArticleUpdate]):
    
    async def find_by_filters(
        self,
        author_id: int = None,
        category_id: int = None,
        is_published: bool = None,
        tags: list[str] = None,
        created_after: datetime = None,
        created_before: datetime = None,
        skip: int = 0,
        limit: int = 20
    ) -> list[Article]:
        """复杂条件查询"""
        query = select(Article)
        
        if author_id:
            query = query.where(Article.author_id == author_id)
        
        if category_id:
            query = query.where(Article.category_id == category_id)
        
        if is_published is not None:
            query = query.where(Article.is_published == is_published)
        
        if tags:
            # 假设 tags 是 JSONB 列
            for tag in tags:
                query = query.where(Article.tags.contains([tag]))
        
        if created_after:
            query = query.where(Article.created_at >= created_after)
        
        if created_before:
            query = query.where(Article.created_at <= created_before)
        
        query = query.order_by(Article.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
```

### 聚合查询

```python
from sqlalchemy import func, case

class OrderRepository(BaseRepository):
    
    async def get_daily_stats(
        self,
        start_date: date,
        end_date: date
    ) -> list[dict]:
        """获取每日订单统计"""
        result = await self.db.execute(
            select(
                func.date(Order.created_at).label("date"),
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("total_amount"),
                func.avg(Order.total_amount).label("avg_amount")
            )
            .where(
                func.date(Order.created_at).between(start_date, end_date)
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        
        return [
            {
                "date": row.date,
                "order_count": row.order_count,
                "total_amount": float(row.total_amount or 0),
                "avg_amount": float(row.avg_amount or 0)
            }
            for row in result
        ]
    
    async def get_status_distribution(self) -> dict[str, int]:
        """获取订单状态分布"""
        result = await self.db.execute(
            select(
                Order.status,
                func.count(Order.id).label("count")
            )
            .group_by(Order.status)
        )
        
        return {row.status: row.count for row in result}
```

### 关联查询

```python
from sqlalchemy.orm import selectinload, joinedload

class ArticleRepository(BaseRepository):
    
    async def get_with_author(self, article_id: int) -> Article | None:
        """获取文章及作者信息"""
        result = await self.db.execute(
            select(Article)
            .options(joinedload(Article.author))
            .where(Article.id == article_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_comments(self, article_id: int) -> Article | None:
        """获取文章及评论"""
        result = await self.db.execute(
            select(Article)
            .options(
                selectinload(Article.comments)
                .selectinload(Comment.author)
            )
            .where(Article.id == article_id)
        )
        return result.scalar_one_or_none()
    
    async def get_popular_articles(self, limit: int = 10) -> list[Article]:
        """获取热门文章（带作者和评论数）"""
        result = await self.db.execute(
            select(
                Article,
                func.count(Comment.id).label("comment_count")
            )
            .outerjoin(Article.comments)
            .options(joinedload(Article.author))
            .where(Article.is_published == True)
            .group_by(Article.id)
            .order_by(func.count(Comment.id).desc())
            .limit(limit)
        )
        
        return result.scalars().unique().all()
```

---

## 最佳实践

### 1. 事务管理

```python
async def transfer_balance(
    self,
    from_user_id: int,
    to_user_id: int,
    amount: float
):
    """转账操作"""
    async with self.db.begin():  # 开启事务
        from_user = await self.get(from_user_id)
        to_user = await self.get(to_user_id)
        
        if from_user.balance < amount:
            raise InsufficientBalanceError()
        
        from_user.balance -= amount
        to_user.balance += amount
        # 事务自动提交或回滚
```

### 2. 批量操作

```python
async def bulk_create(
    self,
    items: list[CreateSchemaType]
) -> list[ModelType]:
    """批量创建"""
    db_objs = [
        self.model(**item.model_dump())
        for item in items
    ]
    self.db.add_all(db_objs)
    await self.db.commit()
    
    for obj in db_objs:
        await self.db.refresh(obj)
    
    return db_objs

async def bulk_update(
    self,
    ids: list[int],
    update_data: dict
) -> int:
    """批量更新"""
    result = await self.db.execute(
        update(self.model)
        .where(self.model.id.in_(ids))
        .values(**update_data)
    )
    await self.db.commit()
    return result.rowcount
```

### 3. 软删除支持

```python
class SoftDeleteRepository(BaseRepository):
    """支持软删除的仓储"""
    
    async def get(self, id: int) -> ModelType | None:
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.id == id,
                self.model.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def soft_delete(self, db_obj: ModelType) -> None:
        db_obj.is_deleted = True
        db_obj.deleted_at = datetime.utcnow()
        await self.db.commit()
    
    async def restore(self, id: int) -> ModelType | None:
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        db_obj = result.scalar_one_or_none()
        if db_obj:
            db_obj.is_deleted = False
            db_obj.deleted_at = None
            await self.db.commit()
        return db_obj
```

---

## 注意事项

1. **单一职责**: 每个仓储只负责一个模型的数据访问
2. **依赖注入**: 通过构造函数注入数据库会话
3. **类型提示**: 使用泛型提供完整的类型支持
4. **异步操作**: 所有数据库操作使用 async/await
5. **事务边界**: 在服务层或仓储方法中明确事务边界
6. **预加载**: 合理使用 selectinload/joinedload 避免 N+1 问题
7. **测试友好**: 仓储接口便于 Mock 和单元测试
