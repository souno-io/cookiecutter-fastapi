"""
数据库操作的基础仓储模式实现。

提供可以为特定模型扩展的通用 CRUD 操作。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.base import Base


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    带有 CRUD 操作的基础仓储类。
    
    提供：
    - 类型安全的通用 CRUD 操作
    - 分页支持
    - 过滤和排序
    
    用法：
        class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
            pass
        
        user_repo = UserRepository(User)
        users = await user_repo.get_multi(db)
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        使用模型类初始化仓储。
        
        参数：
            model: SQLAlchemy 模型类
        """
        self.model = model
    
    async def get(
        self, 
        db: AsyncSession, 
        id: Any,
    ) -> Optional[ModelType]:
        """
        根据 ID 获取单条记录。
        
        参数：
            db: 数据库会话
            id: 记录 ID
            
        返回：
            模型实例或 None
        """
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        field_value: Any,
    ) -> Optional[ModelType]:
        """
        根据任意字段获取单条记录。
        
        参数：
            db: 数据库会话
            field_name: 要过滤的字段名
            field_value: 要匹配的字段值
            
        返回：
            模型实例或 None
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            return None
        
        result = await db.execute(
            select(self.model).where(field == field_value)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """
        获取多条记录，支持分页和过滤。
        
        参数：
            db: 数据库会话
            skip: 跳过的记录数
            limit: 返回的最大记录数
            order_by: 排序字段名
            order_desc: 如果为 True 则降序
            filters: 用于过滤的字段-值对字典
            
        返回：
            模型实例列表
        """
        query = select(self.model)
        
        # 应用过滤器
        if filters:
            for field_name, value in filters.items():
                field = getattr(self.model, field_name, None)
                if field is not None:
                    query = query.where(field == value)
        
        # 应用排序
        if order_by:
            order_field = getattr(self.model, order_by, None)
            if order_field is not None:
                query = query.order_by(
                    order_field.desc() if order_desc else order_field
                )
        
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def count(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        统计记录数量，支持可选过滤。
        
        参数：
            db: 数据库会话
            filters: 用于过滤的字段-值对字典
            
        返回：
            匹配的记录数
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for field_name, value in filters.items():
                field = getattr(self.model, field_name, None)
                if field is not None:
                    query = query.where(field == value)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """
        创建新记录。
        
        参数：
            db: 数据库会话
            obj_in: Pydantic 模式或字段值字典
            
        返回：
            创建的模型实例
        """
        if isinstance(obj_in, dict):
            obj_data = obj_in
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)
        
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """
        更新现有记录。
        
        参数：
            db: 数据库会话
            db_obj: 现有的模型实例
            obj_in: Pydantic 模式或更新值字典
            
        返回：
            更新后的模型实例
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Any,
    ) -> Optional[ModelType]:
        """
        根据 ID 删除记录。
        
        参数：
            db: 数据库会话
            id: 记录 ID
            
        返回：
            删除的模型实例或 None
        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj
    
    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
    ) -> List[ModelType]:
        """
        批量创建记录。
        
        参数：
            db: 数据库会话
            objs_in: Pydantic 模式或字典列表
            
        返回：
            创建的模型实例列表
        """
        db_objs = []
        for obj_in in objs_in:
            if isinstance(obj_in, dict):
                obj_data = obj_in
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)
            db_objs.append(self.model(**obj_data))
        
        db.add_all(db_objs)
        await db.flush()
        
        for obj in db_objs:
            await db.refresh(obj)
        
        return db_objs
    
    async def exists(
        self,
        db: AsyncSession,
        id: Any,
    ) -> bool:
        """
        检查记录是否存在。
        
        参数：
            db: 数据库会话
            id: 记录 ID
            
        返回：
            如果记录存在则返回 True
        """
        result = await db.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None
