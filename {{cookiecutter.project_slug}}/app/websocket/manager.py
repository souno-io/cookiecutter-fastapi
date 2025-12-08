"""
WebSocket 连接管理器，用于处理多个连接。
"""
{%- if cookiecutter.include_websocket == "yes" %}

import json
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket 连接管理器。
    
    管理活跃连接并提供以下方法：
    - 广播消息给所有连接
    - 发送消息给特定用户或群组
    - 管理连接生命周期
    
    功能：
    - 支持房间/频道的分组消息
    - 用户特定连接
    - 广播能力
    """
    
    def __init__(self):
        # 活跃连接：{connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 用户到连接的映射：{user_id: Set[connection_id]}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # 房间/频道成员：{room_id: Set[connection_id]}
        self.rooms: Dict[str, Set[str]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        """
        接受并注册新的 WebSocket 连接。
        
        参数：
            websocket: WebSocket 实例
            connection_id: 唯一连接标识符
            user_id: 可选的用户 ID，用于用户特定消息
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
    
    def disconnect(
        self,
        connection_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        """
        从活跃连接中移除 WebSocket 连接。
        
        参数：
            connection_id: 要移除的连接标识符
            user_id: 可选的用户 ID，用于清理用户映射
        """
        # 从活跃连接中移除
        self.active_connections.pop(connection_id, None)
        
        # 从用户连接中移除
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # 从所有房间中移除
        for room_id in list(self.rooms.keys()):
            self.rooms[room_id].discard(connection_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(
        self,
        message: Any,
        connection_id: str,
    ) -> bool:
        """
        发送消息到特定连接。
        
        参数：
            message: 要发送的消息（字典将被 JSON 编码）
            connection_id: 目标连接 ID
            
        返回：
            消息发送成功返回 True
        """
        websocket = self.active_connections.get(connection_id)
        if not websocket:
            return False
        
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            return False
    
    async def send_to_user(
        self,
        message: Any,
        user_id: str,
    ) -> int:
        """
        发送消息到特定用户的所有连接。
        
        参数：
            message: 要发送的消息
            user_id: 目标用户 ID
            
        返回：
            收到消息的连接数量
        """
        connection_ids = self.user_connections.get(user_id, set())
        sent = 0
        
        for connection_id in connection_ids:
            if await self.send_personal_message(message, connection_id):
                sent += 1
        
        return sent
    
    async def broadcast(
        self,
        message: Any,
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        广播消息到所有已连接的客户端。
        
        参数：
            message: 要广播的消息
            exclude: 要排除的连接 ID 集合
            
        返回：
            收到消息的连接数量
        """
        exclude = exclude or set()
        sent = 0
        
        for connection_id in self.active_connections:
            if connection_id not in exclude:
                if await self.send_personal_message(message, connection_id):
                    sent += 1
        
        return sent
    
    # 房间/频道方法
    
    def join_room(self, connection_id: str, room_id: str) -> None:
        """将连接添加到房间。"""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(connection_id)
        logger.info(f"Connection {connection_id} joined room {room_id}")
    
    def leave_room(self, connection_id: str, room_id: str) -> None:
        """从房间中移除连接。"""
        if room_id in self.rooms:
            self.rooms[room_id].discard(connection_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        logger.info(f"Connection {connection_id} left room {room_id}")
    
    async def send_to_room(
        self,
        message: Any,
        room_id: str,
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        发送消息到房间中的所有连接。
        
        参数：
            message: 要发送的消息
            room_id: 目标房间 ID
            exclude: 要排除的连接 ID 集合
            
        返回：
            收到消息的连接数量
        """
        exclude = exclude or set()
        connection_ids = self.rooms.get(room_id, set())
        sent = 0
        
        for connection_id in connection_ids:
            if connection_id not in exclude:
                if await self.send_personal_message(message, connection_id):
                    sent += 1
        
        return sent
    
    def get_room_members(self, room_id: str) -> Set[str]:
        """获取房间中的所有连接 ID。"""
        return self.rooms.get(room_id, set()).copy()
    
    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户的活跃连接数量。"""
        return len(self.user_connections.get(user_id, set()))
    
    @property
    def connection_count(self) -> int:
        """获取活跃连接总数。"""
        return len(self.active_connections)


# 全局连接管理器实例
connection_manager = ConnectionManager()
{%- endif %}
