"""
应用程序通用数据模式定义。
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


DataT = TypeVar("DataT")


class BaseSchema(BaseModel):
    """带有通用配置的基础模式。"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """时间戳字段混入类。"""
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    通用分页响应模式。
    
    用法：
        PaginatedResponse[UserResponse]
    """
    
    items: List[DataT]
    total: int
    page: int
    page_size: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: List[DataT],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[DataT]":
        """创建分页响应。"""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


class Response(BaseModel, Generic[DataT]):
    """通用 API 响应模式。"""
    
    data: Optional[DataT] = None
    message: str = "success"
    success: bool = True


class MessageResponse(BaseModel):
    """简单消息响应。"""
    
    message: str
    success: bool = True
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    """健康检查响应。"""
    
    status: str = "healthy"
    version: str
    environment: str
    database: str = "connected"
    {%- if cookiecutter.use_redis == "yes" %}
    redis: str = "connected"
    {%- endif %}


class ErrorResponse(BaseModel):
    """错误响应数据模式。"""
    
    detail: str
    error_code: Optional[str] = None
    errors: Optional[List[dict]] = None


class QueryParams(BaseModel):
    """列表端点的通用查询参数。"""
    
    page: int = 1
    page_size: int = 20
    order_by: Optional[str] = None
    order_desc: bool = False
    search: Optional[str] = None
    
    @property
    def skip(self) -> int:
        """计算分页偏移量。"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """获取分页限制数量。"""
        return self.page_size
