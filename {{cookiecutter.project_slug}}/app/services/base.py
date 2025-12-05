"""
基础服务类，包含通用功能。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.base import Base
from app.db.repositories.base import BaseRepository


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    基础服务类，提供业务逻辑层。
    
    包装仓储层操作，添加额外的业务逻辑、
    验证和错误处理。
    
    用法示例：
        class UserService(BaseService[User, UserCreate, UserUpdate]):
            def __init__(self):
                super().__init__(User)
            
            async def custom_method(self, db: AsyncSession) -> ...:
                ...
    """
    
    def __init__(self, model: Type[ModelType]):
        """使用模型和仓储初始化服务。"""
        self.model = model
        self.repository = BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType](model)
    
    async def get(
        self,
        db: AsyncSession,
        id: Any,
    ) -> Optional[ModelType]:
        """根据 ID 获取单条记录。"""
        return await self.repository.get(db, id)
    
    async def get_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        field_value: Any,
    ) -> Optional[ModelType]:
        """根据任意字段获取单条记录。"""
        return await self.repository.get_by_field(db, field_name, field_value)
    
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
        """获取多条记录，支持分页和过滤。"""
        return await self.repository.get_multi(
            db,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
            filters=filters,
        )
    
    async def count(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """统计记录数量，支持可选过滤。"""
        return await self.repository.count(db, filters)
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """创建新记录。"""
        return await self.repository.create(db, obj_in=obj_in)
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """更新现有记录。"""
        return await self.repository.update(db, db_obj=db_obj, obj_in=obj_in)
    
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Any,
    ) -> Optional[ModelType]:
        """根据 ID 删除记录。"""
        return await self.repository.delete(db, id=id)
    
    async def exists(
        self,
        db: AsyncSession,
        id: Any,
    ) -> bool:
        """检查记录是否存在。"""
        return await self.repository.exists(db, id)
