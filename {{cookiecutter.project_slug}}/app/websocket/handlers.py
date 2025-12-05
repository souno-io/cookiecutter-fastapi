"""
WebSocket 处理器和端点实现。
"""
{%- if cookiecutter.include_websocket == "yes" %}

import json
import logging
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import security_manager
from app.db.session import get_db
from app.websocket.manager import connection_manager


logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketHandler:
    """
    基础 WebSocket 处理器，包含通用功能。
    
    提供：
    - 基于类型的消息路由
    - 错误处理
    - 认证支持
    """
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
    
    def on(self, message_type: str):
        """
        Decorator to register a handler for a specific message type.
        
        Usage:
            handler = WebSocketHandler()
            
            @handler.on("chat")
            async def handle_chat(websocket, data, connection_id):
                ...
        """
        def decorator(func: Callable):
            self.handlers[message_type] = func
            return func
        return decorator
    
    async def handle_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
        connection_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Route and handle incoming messages.
        
        Expected message format:
        {
            "type": "message_type",
            "data": {...}
        }
        """
        message_type = message.get("type")
        data = message.get("data", {})
        
        handler = self.handlers.get(message_type)
        
        if not handler:
            return {
                "type": "error",
                "data": {"message": f"Unknown message type: {message_type}"}
            }
        
        try:
            return await handler(websocket, data, connection_id, user_id)
        except Exception as e:
            logger.error(f"Handler error for {message_type}: {e}")
            return {
                "type": "error",
                "data": {"message": str(e)}
            }


# Create default handler
ws_handler = WebSocketHandler()


# Register default handlers
@ws_handler.on("ping")
async def handle_ping(websocket, data, connection_id, user_id):
    """处理 ping 消息。"""
    return {"type": "pong", "data": {}}


@ws_handler.on("join_room")
async def handle_join_room(websocket, data, connection_id, user_id):
    """处理加入房间请求。"""
    room_id = data.get("room_id")
    if not room_id:
        return {"type": "error", "data": {"message": "room_id required"}}
    
    connection_manager.join_room(connection_id, room_id)
    return {
        "type": "room_joined",
        "data": {
            "room_id": room_id,
            "members": len(connection_manager.get_room_members(room_id)),
        }
    }


@ws_handler.on("leave_room")
async def handle_leave_room(websocket, data, connection_id, user_id):
    """处理离开房间请求。"""
    room_id = data.get("room_id")
    if not room_id:
        return {"type": "error", "data": {"message": "room_id required"}}
    
    connection_manager.leave_room(connection_id, room_id)
    return {"type": "room_left", "data": {"room_id": room_id}}


@ws_handler.on("room_message")
async def handle_room_message(websocket, data, connection_id, user_id):
    """处理发送到房间的消息。"""
    room_id = data.get("room_id")
    message = data.get("message")
    
    if not room_id or not message:
        return {"type": "error", "data": {"message": "room_id and message required"}}
    
    # 广播到房间
    await connection_manager.send_to_room(
        {
            "type": "room_message",
            "data": {
                "room_id": room_id,
                "message": message,
                "sender_id": user_id,
            }
        },
        room_id,
        exclude={connection_id},  # 不发送给发送者
    )
    
    return {"type": "message_sent", "data": {"room_id": room_id}}


@ws_handler.on("broadcast")
async def handle_broadcast(websocket, data, connection_id, user_id):
    """处理广播消息（仅管理员）。"""
    message = data.get("message")
    
    if not message:
        return {"type": "error", "data": {"message": "message required"}}
    
    # 在生产环境中，在此添加管理员检查
    sent = await connection_manager.broadcast(
        {"type": "broadcast", "data": {"message": message}},
        exclude={connection_id},
    )
    
    return {"type": "broadcast_sent", "data": {"recipients": sent}}


# WebSocket 端点
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Main WebSocket endpoint.
    
    Connection URL: ws://host/ws?token=<jwt_token>
    
    Message format (JSON):
    {
        "type": "message_type",
        "data": {...}
    }
    """
    connection_id = str(uuid4())
    user_id = None
    
    # 如果提供了令牌则进行验证
    if token:
        token_data = security_manager.decode_token(token)
        if token_data and token_data.token_type == "access":
            user_id = token_data.user_id
    
    # 接受连接
    await connection_manager.connect(websocket, connection_id, user_id)
    
    try:
        # 发送连接确认
        await websocket.send_json({
            "type": "connected",
            "data": {
                "connection_id": connection_id,
                "user_id": user_id,
            }
        })
        
        # 消息循环
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"}
                })
                continue
            
            # 处理消息
            response = await ws_handler.handle_message(
                websocket, message, connection_id, user_id
            )
            
            if response:
                await websocket.send_json(response)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(connection_id, user_id)


@router.websocket("/ws/notifications")
async def notification_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Notification-specific WebSocket endpoint.
    
    Requires authentication.
    """
    # 验证令牌
    token_data = security_manager.decode_token(token)
    
    if not token_data or token_data.token_type != "access":
        await websocket.close(code=4001)  # Unauthorized
        return
    
    user_id = token_data.user_id
    connection_id = str(uuid4())
    
    await connection_manager.connect(websocket, connection_id, user_id)
    
    try:
        await websocket.send_json({
            "type": "subscribed",
            "data": {"channel": "notifications"}
        })
        
        while True:
            # 保持连接存活
            data = await websocket.receive_text()
            
            # 处理 ping
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(connection_id, user_id)
{%- endif %}
