"""
分页工具模块。

提供统一的分页处理功能。
"""

from math import ceil
from typing import Generic, List, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel


T = TypeVar("T")


class PaginationParams:
    """分页参数依赖。"""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
        order_by: Optional[str] = Query(None, description="排序字段"),
        order_desc: bool = Query(False, description="是否降序"),
    ):
        """
        初始化分页参数。
        
        参数：
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            order_desc: 是否降序
        """
        self.page = page
        self.page_size = page_size
        self.order_by = order_by
        self.order_desc = order_desc
    
    @property
    def offset(self) -> int:
        """计算偏移量。"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """获取限制数量。"""
        return self.page_size


class PageInfo(BaseModel):
    """分页信息模型。"""
    
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型。
    
    用法：
        @router.get("/items", response_model=PaginatedResponse[ItemSchema])
        async def list_items(pagination: PaginationParams = Depends()):
            items, total = await get_items_with_count(
                offset=pagination.offset,
                limit=pagination.limit,
            )
            return create_paginated_response(items, total, pagination)
    """
    
    data: List[T]
    pagination: PageInfo
    
    class Config:
        arbitrary_types_allowed = True


def create_paginated_response(
    items: List[T],
    total: int,
    params: PaginationParams,
) -> PaginatedResponse[T]:
    """
    创建分页响应。
    
    参数：
        items: 数据列表
        total: 总数量
        params: 分页参数
        
    返回：
        分页响应对象
    """
    total_pages = ceil(total / params.page_size) if total > 0 else 0
    
    return PaginatedResponse(
        data=items,
        pagination=PageInfo(
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        ),
    )


class CursorPaginationParams:
    """游标分页参数（适合大数据量）。"""
    
    def __init__(
        self,
        cursor: Optional[str] = Query(None, description="游标（上一页最后一条记录的 ID）"),
        limit: int = Query(20, ge=1, le=100, description="返回数量"),
    ):
        """
        初始化游标分页参数。
        
        参数：
            cursor: 游标值
            limit: 返回数量
        """
        self.cursor = cursor
        self.limit = limit


class CursorPageInfo(BaseModel):
    """游标分页信息。"""
    
    limit: int
    has_next: bool
    next_cursor: Optional[str] = None


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """游标分页响应模型。"""
    
    data: List[T]
    pagination: CursorPageInfo


def create_cursor_paginated_response(
    items: List[T],
    params: CursorPaginationParams,
    get_cursor: callable = None,
) -> CursorPaginatedResponse[T]:
    """
    创建游标分页响应。
    
    参数：
        items: 数据列表
        params: 分页参数
        get_cursor: 获取游标值的函数，默认使用 item.id
        
    返回：
        游标分页响应对象
    """
    has_next = len(items) > params.limit
    
    if has_next:
        items = items[:params.limit]
    
    next_cursor = None
    if has_next and items:
        last_item = items[-1]
        if get_cursor:
            next_cursor = get_cursor(last_item)
        elif hasattr(last_item, "id"):
            next_cursor = str(last_item.id)
    
    return CursorPaginatedResponse(
        data=items,
        pagination=CursorPageInfo(
            limit=params.limit,
            has_next=has_next,
            next_cursor=next_cursor,
        ),
    )
