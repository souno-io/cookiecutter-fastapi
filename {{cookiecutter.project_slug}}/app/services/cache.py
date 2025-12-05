"""
Redis 缓存服务模块。

提供统一的缓存操作接口，支持：
- 键值存储
- 过期时间
- 缓存装饰器
- 分布式锁
- 发布/订阅
"""

import asyncio
import functools
import hashlib
import json
import logging
from datetime import timedelta
from typing import Any, Callable, Optional, Type, TypeVar, Union

from redis import asyncio as aioredis
from pydantic import BaseModel

from app.core.config import settings


logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheService:
    """
    Redis 缓存服务类。
    
    提供异步缓存操作接口。
    """
    
    def __init__(self, redis_url: str = None):
        """
        初始化缓存服务。
        
        参数：
            redis_url: Redis 连接 URL
        """
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self._redis: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """建立 Redis 连接。"""
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    self._redis = await aioredis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                    )
                    logger.info("Redis 连接成功")
    
    async def disconnect(self) -> None:
        """关闭 Redis 连接。"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis 连接已关闭")
    
    @property
    async def redis(self) -> aioredis.Redis:
        """获取 Redis 客户端实例。"""
        if self._redis is None:
            await self.connect()
        return self._redis
    
    async def get(
        self, 
        key: str, 
        model: Type[T] = None,
    ) -> Optional[Union[str, T]]:
        """
        获取缓存值。
        
        参数：
            key: 缓存键
            model: Pydantic 模型类（用于反序列化）
            
        返回：
            缓存值，不存在返回 None
        """
        client = await self.redis
        value = await client.get(key)
        
        if value is None:
            return None
        
        if model:
            try:
                data = json.loads(value)
                return model.model_validate(data)
            except Exception as e:
                logger.warning(f"缓存反序列化失败: {key} - {e}")
                return None
        
        return value
    
    async def set(
        self,
        key: str,
        value: Union[str, BaseModel, dict],
        expire: Union[int, timedelta] = None,
    ) -> bool:
        """
        设置缓存值。
        
        参数：
            key: 缓存键
            value: 缓存值（字符串、Pydantic 模型或字典）
            expire: 过期时间（秒或 timedelta）
            
        返回：
            设置成功返回 True
        """
        client = await self.redis
        
        # 序列化值
        if isinstance(value, BaseModel):
            value = value.model_dump_json()
        elif isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        
        # 处理过期时间
        if isinstance(expire, timedelta):
            expire = int(expire.total_seconds())
        
        await client.set(key, value, ex=expire)
        return True
    
    async def delete(self, *keys: str) -> int:
        """
        删除缓存。
        
        参数：
            keys: 要删除的键
            
        返回：
            实际删除的键数量
        """
        if not keys:
            return 0
        
        client = await self.redis
        return await client.delete(*keys)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在。"""
        client = await self.redis
        return await client.exists(key) > 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间。"""
        client = await self.redis
        return await client.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间（秒）。"""
        client = await self.redis
        return await client.ttl(key)
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """原子递增。"""
        client = await self.redis
        return await client.incr(key, amount)
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """原子递减。"""
        client = await self.redis
        return await client.decr(key, amount)
    
    async def get_many(self, *keys: str) -> dict:
        """批量获取。"""
        if not keys:
            return {}
        
        client = await self.redis
        values = await client.mget(keys)
        return {key: value for key, value in zip(keys, values) if value is not None}
    
    async def set_many(
        self,
        mapping: dict,
        expire: int = None,
    ) -> bool:
        """批量设置。"""
        client = await self.redis
        
        # 序列化值
        serialized = {}
        for key, value in mapping.items():
            if isinstance(value, BaseModel):
                value = value.model_dump_json()
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            serialized[key] = value
        
        await client.mset(serialized)
        
        # 设置过期时间
        if expire:
            for key in serialized:
                await client.expire(key, expire)
        
        return True
    
    async def keys(self, pattern: str = "*") -> list:
        """获取匹配的键。"""
        client = await self.redis
        return await client.keys(pattern)
    
    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有键。"""
        keys = await self.keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0
    
    # ==================== 分布式锁 ====================
    
    async def acquire_lock(
        self,
        name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: float = None,
    ) -> Optional[str]:
        """
        获取分布式锁。
        
        参数：
            name: 锁名称
            timeout: 锁超时时间（秒）
            blocking: 是否阻塞等待
            blocking_timeout: 阻塞超时时间
            
        返回：
            锁令牌，获取失败返回 None
        """
        import uuid
        
        client = await self.redis
        lock_key = f"lock:{name}"
        token = str(uuid.uuid4())
        
        if blocking:
            end_time = None
            if blocking_timeout:
                end_time = asyncio.get_event_loop().time() + blocking_timeout
            
            while True:
                if await client.set(lock_key, token, nx=True, ex=timeout):
                    return token
                
                if end_time and asyncio.get_event_loop().time() >= end_time:
                    return None
                
                await asyncio.sleep(0.1)
        else:
            if await client.set(lock_key, token, nx=True, ex=timeout):
                return token
            return None
    
    async def release_lock(self, name: str, token: str) -> bool:
        """
        释放分布式锁。
        
        参数：
            name: 锁名称
            token: 锁令牌
            
        返回：
            释放成功返回 True
        """
        client = await self.redis
        lock_key = f"lock:{name}"
        
        # 使用 Lua 脚本确保原子性
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = await client.eval(script, 1, lock_key, token)
        return result == 1
    
    # ==================== 发布/订阅 ====================
    
    async def publish(self, channel: str, message: Any) -> int:
        """
        发布消息到频道。
        
        参数：
            channel: 频道名称
            message: 消息内容
            
        返回：
            接收到消息的订阅者数量
        """
        client = await self.redis
        
        if isinstance(message, (dict, list)):
            message = json.dumps(message, ensure_ascii=False)
        elif isinstance(message, BaseModel):
            message = message.model_dump_json()
        
        return await client.publish(channel, message)
    
    async def subscribe(
        self,
        *channels: str,
        callback: Callable[[str, str], Any],
    ) -> None:
        """
        订阅频道。
        
        参数：
            channels: 频道名称
            callback: 消息回调函数 (channel, message) -> None
        """
        client = await self.redis
        pubsub = client.pubsub()
        
        await pubsub.subscribe(*channels)
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                await callback(message["channel"], message["data"])


# 全局缓存服务实例
cache_service = CacheService()


def cached(
    expire: int = 300,
    prefix: str = "",
    key_builder: Callable = None,
):
    """
    缓存装饰器。
    
    用法：
        @cached(expire=60, prefix="user")
        async def get_user(user_id: int):
            ...
    
    参数：
        expire: 缓存过期时间（秒）
        prefix: 缓存键前缀
        key_builder: 自定义键生成函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认使用函数名 + 参数哈希
                key_parts = [prefix or func.__name__]
                
                if args:
                    key_parts.append(str(args))
                if kwargs:
                    key_parts.append(str(sorted(kwargs.items())))
                
                raw_key = ":".join(key_parts)
                cache_key = f"cache:{hashlib.md5(raw_key.encode()).hexdigest()}"
            
            # 尝试从缓存获取
            cached_value = await cache_service.get(cache_key)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except:
                    return cached_value
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            if result is not None:
                if isinstance(result, BaseModel):
                    await cache_service.set(cache_key, result, expire)
                elif isinstance(result, (dict, list)):
                    await cache_service.set(cache_key, result, expire)
                else:
                    await cache_service.set(cache_key, str(result), expire)
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(*patterns: str):
    """
    缓存失效装饰器。
    
    用法：
        @cache_invalidate("user:*", "list:users")
        async def update_user(user_id: int, data: dict):
            ...
    
    参数：
        patterns: 要清除的缓存模式
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 清除匹配的缓存
            for pattern in patterns:
                await cache_service.clear_pattern(pattern)
            
            return result
        
        return wrapper
    return decorator
