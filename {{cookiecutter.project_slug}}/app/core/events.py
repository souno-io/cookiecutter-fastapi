"""
事件发布/订阅系统。

提供应用内的事件驱动架构支持，支持：
- 同步事件处理
- 异步事件处理
- 事件中间件
- 事件优先级
"""

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union

from pydantic import BaseModel


logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Event")


class EventPriority(int, Enum):
    """事件处理优先级。"""
    
    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100


class Event(BaseModel):
    """
    事件基类。
    
    所有自定义事件应继承此类。
    """
    
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.event_type:
            self.event_type = self.__class__.__name__
    
    class Config:
        arbitrary_types_allowed = True


# ==================== 预定义事件 ====================

class UserCreatedEvent(Event):
    """用户创建事件。"""
    
    event_type: str = "user.created"
    user_id: int
    email: str
    username: str


class UserUpdatedEvent(Event):
    """用户更新事件。"""
    
    event_type: str = "user.updated"
    user_id: int
    changes: Dict[str, Any] = {}


class UserDeletedEvent(Event):
    """用户删除事件。"""
    
    event_type: str = "user.deleted"
    user_id: int


class UserLoginEvent(Event):
    """用户登录事件。"""
    
    event_type: str = "user.login"
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class UserLogoutEvent(Event):
    """用户登出事件。"""
    
    event_type: str = "user.logout"
    user_id: int


class PasswordChangedEvent(Event):
    """密码变更事件。"""
    
    event_type: str = "user.password_changed"
    user_id: int


class RoleAssignedEvent(Event):
    """角色分配事件。"""
    
    event_type: str = "role.assigned"
    user_id: int
    role_id: int
    role_name: str


class FileUploadedEvent(Event):
    """文件上传事件。"""
    
    event_type: str = "file.uploaded"
    user_id: Optional[int] = None
    filename: str
    filepath: str
    size: int


# ==================== 事件处理器 ====================

@dataclass
class EventHandler:
    """事件处理器包装类。"""
    
    handler: Callable
    priority: EventPriority = EventPriority.NORMAL
    is_async: bool = False
    filters: List[Callable[[Event], bool]] = field(default_factory=list)
    
    def should_handle(self, event: Event) -> bool:
        """检查是否应处理此事件。"""
        return all(f(event) for f in self.filters)


class EventBus:
    """
    事件总线类。
    
    管理事件的发布和订阅。
    """
    
    def __init__(self):
        """初始化事件总线。"""
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._middleware: List[Callable] = []
        self._lock = asyncio.Lock()
    
    def subscribe(
        self,
        event_type: Union[str, Type[Event]],
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        filters: List[Callable[[Event], bool]] = None,
    ) -> None:
        """
        订阅事件。
        
        参数：
            event_type: 事件类型（类或字符串）
            handler: 事件处理函数
            priority: 处理优先级
            filters: 事件过滤器列表
        """
        if isinstance(event_type, type):
            event_type = event_type.__name__
        
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        is_async = asyncio.iscoroutinefunction(handler)
        
        event_handler = EventHandler(
            handler=handler,
            priority=priority,
            is_async=is_async,
            filters=filters or [],
        )
        
        self._handlers[event_type].append(event_handler)
        
        # 按优先级排序
        self._handlers[event_type].sort(
            key=lambda h: h.priority.value,
            reverse=True,
        )
        
        logger.debug(f"订阅事件: {event_type} -> {handler.__name__}")
    
    def unsubscribe(
        self,
        event_type: Union[str, Type[Event]],
        handler: Callable,
    ) -> bool:
        """
        取消订阅事件。
        
        参数：
            event_type: 事件类型
            handler: 事件处理函数
            
        返回：
            取消成功返回 True
        """
        if isinstance(event_type, type):
            event_type = event_type.__name__
        
        if event_type not in self._handlers:
            return False
        
        original_count = len(self._handlers[event_type])
        self._handlers[event_type] = [
            h for h in self._handlers[event_type]
            if h.handler != handler
        ]
        
        return len(self._handlers[event_type]) < original_count
    
    def add_middleware(self, middleware: Callable) -> None:
        """
        添加事件中间件。
        
        中间件签名：async def middleware(event, next) -> Any
        """
        self._middleware.append(middleware)
    
    async def publish(self, event: Event) -> List[Any]:
        """
        发布事件。
        
        参数：
            event: 事件对象
            
        返回：
            所有处理器的返回值列表
        """
        event_type = event.event_type or event.__class__.__name__
        
        logger.debug(f"发布事件: {event_type}")
        
        # 执行中间件链
        async def run_handlers():
            return await self._execute_handlers(event, event_type)
        
        # 构建中间件链
        handler = run_handlers
        for middleware in reversed(self._middleware):
            handler = functools.partial(
                self._wrap_middleware,
                middleware,
                event,
                handler,
            )
        
        return await handler()
    
    async def _wrap_middleware(
        self,
        middleware: Callable,
        event: Event,
        next_handler: Callable,
    ) -> Any:
        """包装中间件执行。"""
        if asyncio.iscoroutinefunction(middleware):
            return await middleware(event, next_handler)
        return middleware(event, next_handler)
    
    async def _execute_handlers(
        self,
        event: Event,
        event_type: str,
    ) -> List[Any]:
        """执行事件处理器。"""
        results = []
        
        handlers = self._handlers.get(event_type, [])
        
        for event_handler in handlers:
            if not event_handler.should_handle(event):
                continue
            
            try:
                if event_handler.is_async:
                    result = await event_handler.handler(event)
                else:
                    result = event_handler.handler(event)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"事件处理失败 | 事件: {event_type} | "
                    f"处理器: {event_handler.handler.__name__} | "
                    f"错误: {e}"
                )
        
        return results
    
    def publish_sync(self, event: Event) -> None:
        """
        同步发布事件（创建新的事件循环）。
        
        注意：仅在非异步上下文中使用。
        """
        asyncio.run(self.publish(event))
    
    def clear(self) -> None:
        """清除所有订阅。"""
        self._handlers.clear()
        self._middleware.clear()


# 全局事件总线实例
event_bus = EventBus()


# ==================== 装饰器 ====================

def on_event(
    event_type: Union[str, Type[Event]],
    priority: EventPriority = EventPriority.NORMAL,
    filters: List[Callable[[Event], bool]] = None,
):
    """
    事件订阅装饰器。
    
    用法：
        @on_event(UserCreatedEvent)
        async def handle_user_created(event: UserCreatedEvent):
            print(f"新用户: {event.username}")
    
        @on_event("user.login", priority=EventPriority.HIGH)
        async def handle_user_login(event: UserLoginEvent):
            print(f"用户登录: {event.user_id}")
    """
    def decorator(func: Callable) -> Callable:
        event_bus.subscribe(
            event_type=event_type,
            handler=func,
            priority=priority,
            filters=filters,
        )
        return func
    return decorator


def emit_event(event_type: Type[T]):
    """
    事件发射装饰器。
    
    用法：
        @emit_event(UserCreatedEvent)
        async def create_user(data):
            user = await save_user(data)
            return UserCreatedEvent(
                user_id=user.id,
                email=user.email,
                username=user.username,
            )
    
    装饰的函数返回值将作为事件发布。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if isinstance(result, Event):
                await event_bus.publish(result)
            
            return result
        return wrapper
    return decorator


# ==================== 事件处理器示例 ====================

@on_event(UserCreatedEvent)
async def log_user_created(event: UserCreatedEvent):
    """记录用户创建日志。"""
    logger.info(f"用户创建 | ID: {event.user_id} | 邮箱: {event.email}")


@on_event(UserLoginEvent)
async def log_user_login(event: UserLoginEvent):
    """记录用户登录日志。"""
    logger.info(
        f"用户登录 | ID: {event.user_id} | "
        f"IP: {event.ip_address} | "
        f"UA: {event.user_agent}"
    )
