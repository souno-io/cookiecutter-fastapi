# WebSocket 模块

本模块提供 WebSocket 实时通信功能，包括连接管理、消息处理和房间广播。

## 目录

- [模块结构](#模块结构)
- [连接管理器](#连接管理器)
- [消息处理器](#消息处理器)
- [房间管理](#房间管理)
- [认证与授权](#认证与授权)
- [使用示例](#使用示例)
- [客户端集成](#客户端集成)

---

## 模块结构

```
websocket/
├── __init__.py      # 模块导出
├── manager.py       # 连接管理器
└── handlers.py      # 消息处理器
```

---

## 连接管理器

### 文件：`manager.py`

管理 WebSocket 连接的生命周期。

### ConnectionManager 类

```python
from app.websocket import ConnectionManager

class ConnectionManager:
    """
    WebSocket 连接管理器
    
    功能：
    - 连接的建立和断开
    - 单播、广播、组播消息
    - 房间管理
    - 连接状态维护
    """
    
    # 连接管理
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str = None,
        groups: list[str] = None
    ) -> str  # 返回连接ID
    
    async def disconnect(self, connection_id: str) -> None
    
    # 消息发送
    async def send_personal(
        self,
        connection_id: str,
        message: dict
    ) -> bool
    
    async def send_to_user(
        self,
        user_id: str,
        message: dict
    ) -> int  # 返回发送成功的连接数
    
    async def broadcast(
        self,
        message: dict,
        exclude: list[str] = None
    ) -> int
    
    async def send_to_group(
        self,
        group: str,
        message: dict,
        exclude: list[str] = None
    ) -> int
    
    # 房间管理
    async def join_group(
        self,
        connection_id: str,
        group: str
    ) -> None
    
    async def leave_group(
        self,
        connection_id: str,
        group: str
    ) -> None
    
    # 状态查询
    def get_connection_count(self) -> int
    def get_group_connections(self, group: str) -> list[str]
    def get_user_connections(self, user_id: str) -> list[str]
```

### 使用示例

```python
from app.websocket import ConnectionManager

# 创建全局管理器实例
manager = ConnectionManager()

# WebSocket 端点
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str
):
    # 建立连接
    connection_id = await manager.connect(websocket, user_id=user_id)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            # 处理消息
            await handle_message(connection_id, data)
            
    except WebSocketDisconnect:
        # 断开连接
        await manager.disconnect(connection_id)
```

---

## 消息处理器

### 文件：`handlers.py`

处理不同类型的 WebSocket 消息。

### WebSocketHandler 类

```python
from app.websocket import WebSocketHandler

class WebSocketHandler:
    """
    WebSocket 消息处理器
    
    支持的消息类型：
    - chat: 聊天消息
    - notification: 通知消息
    - presence: 在线状态
    - typing: 正在输入
    - custom: 自定义消息
    """
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.handlers = {}
    
    def register(self, message_type: str):
        """注册消息处理函数"""
        def decorator(func):
            self.handlers[message_type] = func
            return func
        return decorator
    
    async def handle(
        self,
        connection_id: str,
        message: dict
    ) -> dict | None:
        """处理消息"""
        message_type = message.get("type")
        handler = self.handlers.get(message_type)
        
        if handler:
            return await handler(connection_id, message)
        
        return {"error": f"未知消息类型: {message_type}"}
```

### 注册消息处理器

```python
from app.websocket import WebSocketHandler, ConnectionManager

manager = ConnectionManager()
handler = WebSocketHandler(manager)

# 注册聊天消息处理器
@handler.register("chat")
async def handle_chat(connection_id: str, message: dict):
    """处理聊天消息"""
    target = message.get("to")
    content = message.get("content")
    
    # 发送给目标用户
    sent = await manager.send_to_user(target, {
        "type": "chat",
        "from": message.get("from"),
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"status": "sent", "recipients": sent}

# 注册通知处理器
@handler.register("notification")
async def handle_notification(connection_id: str, message: dict):
    """处理通知消息"""
    # 广播通知
    await manager.broadcast({
        "type": "notification",
        "title": message.get("title"),
        "body": message.get("body")
    })
    
    return {"status": "broadcasted"}

# 注册房间消息处理器
@handler.register("room_message")
async def handle_room_message(connection_id: str, message: dict):
    """处理房间消息"""
    room = message.get("room")
    content = message.get("content")
    
    await manager.send_to_group(room, {
        "type": "room_message",
        "room": room,
        "from": message.get("from"),
        "content": content
    }, exclude=[connection_id])
    
    return {"status": "sent"}
```

---

## 房间管理

### 加入/离开房间

```python
# 加入房间
@handler.register("join_room")
async def handle_join_room(connection_id: str, message: dict):
    room = message.get("room")
    
    await manager.join_group(connection_id, room)
    
    # 通知房间其他成员
    await manager.send_to_group(room, {
        "type": "user_joined",
        "room": room,
        "user": message.get("user")
    }, exclude=[connection_id])
    
    return {"status": "joined", "room": room}

# 离开房间
@handler.register("leave_room")
async def handle_leave_room(connection_id: str, message: dict):
    room = message.get("room")
    
    await manager.leave_group(connection_id, room)
    
    # 通知房间其他成员
    await manager.send_to_group(room, {
        "type": "user_left",
        "room": room,
        "user": message.get("user")
    })
    
    return {"status": "left", "room": room}
```

### 房间列表

```python
# 获取房间成员
def get_room_members(room: str) -> list[str]:
    connection_ids = manager.get_group_connections(room)
    # 获取用户信息
    members = []
    for conn_id in connection_ids:
        user_id = manager.get_user_id(conn_id)
        if user_id:
            members.append(user_id)
    return members

# 获取用户所在房间
def get_user_rooms(user_id: str) -> list[str]:
    connections = manager.get_user_connections(user_id)
    rooms = set()
    for conn_id in connections:
        rooms.update(manager.get_connection_groups(conn_id))
    return list(rooms)
```

---

## 认证与授权

### WebSocket 认证

```python
from fastapi import WebSocket, Query, HTTPException
from app.core.security import SecurityManager

async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(...)
) -> User:
    """WebSocket 连接认证"""
    try:
        payload = SecurityManager.verify_token(token)
        user_id = payload.get("sub")
        
        # 获取用户
        user = await get_user(user_id)
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="用户不存在或已禁用")
            return None
        
        return user
        
    except Exception:
        await websocket.close(code=4001, reason="无效的认证令牌")
        return None

# 使用认证
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    # 认证
    user = await get_current_user_ws(websocket, token)
    if not user:
        return
    
    # 接受连接
    await websocket.accept()
    connection_id = await manager.connect(websocket, user_id=str(user.id))
    
    # ... 处理消息
```

### 权限检查

```python
async def check_room_access(user: User, room: str) -> bool:
    """检查用户是否有权限访问房间"""
    # 公共房间
    if room.startswith("public:"):
        return True
    
    # 私人房间
    if room.startswith("private:"):
        room_id = room.split(":")[1]
        return await is_room_member(user.id, room_id)
    
    # 管理员房间
    if room.startswith("admin:"):
        return user.is_superuser
    
    return False

# 在加入房间时检查权限
@handler.register("join_room")
async def handle_join_room(connection_id: str, message: dict):
    room = message.get("room")
    user = manager.get_connection_user(connection_id)
    
    if not await check_room_access(user, room):
        return {"error": "没有权限加入此房间"}
    
    await manager.join_group(connection_id, room)
    return {"status": "joined"}
```

---

## 使用示例

### 完整的 WebSocket 端点

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from app.websocket import ConnectionManager, WebSocketHandler

app = FastAPI()
manager = ConnectionManager()
handler = WebSocketHandler(manager)

# 注册处理器
@handler.register("ping")
async def handle_ping(connection_id: str, message: dict):
    return {"type": "pong", "timestamp": datetime.utcnow().isoformat()}

@handler.register("chat")
async def handle_chat(connection_id: str, message: dict):
    await manager.send_to_user(message["to"], {
        "type": "chat",
        "from": message["from"],
        "content": message["content"]
    })
    return {"status": "sent"}

# WebSocket 端点
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    # 验证令牌
    try:
        payload = SecurityManager.verify_token(token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001)
        return
    
    # 接受连接
    await websocket.accept()
    connection_id = await manager.connect(websocket, user_id=user_id)
    
    # 发送欢迎消息
    await manager.send_personal(connection_id, {
        "type": "connected",
        "connection_id": connection_id,
        "user_id": user_id
    })
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            # 处理消息
            response = await handler.handle(connection_id, data)
            
            # 发送响应
            if response:
                await manager.send_personal(connection_id, response)
                
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
        
        # 通知其他用户
        await manager.broadcast({
            "type": "user_offline",
            "user_id": user_id
        })
```

### 从 HTTP 端点发送消息

```python
from app.websocket import manager

@router.post("/notifications/broadcast")
async def broadcast_notification(
    notification: NotificationCreate,
    current_user: User = Depends(get_current_superuser)
):
    """广播通知给所有在线用户"""
    sent_count = await manager.broadcast({
        "type": "notification",
        "title": notification.title,
        "body": notification.body,
        "created_at": datetime.utcnow().isoformat()
    })
    
    return {
        "message": "通知已发送",
        "recipients": sent_count
    }

@router.post("/messages/{user_id}")
async def send_message_to_user(
    user_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """发送消息给指定用户"""
    sent_count = await manager.send_to_user(str(user_id), {
        "type": "chat",
        "from": str(current_user.id),
        "content": message.content,
        "created_at": datetime.utcnow().isoformat()
    })
    
    if sent_count == 0:
        # 用户不在线，保存离线消息
        await save_offline_message(user_id, message)
    
    return {"message": "消息已发送", "online": sent_count > 0}
```

---

## 客户端集成

### JavaScript 客户端

```javascript
class WebSocketClient {
    constructor(url, token) {
        this.url = `${url}?token=${token}`;
        this.ws = null;
        this.handlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('WebSocket 已连接');
            this.reconnectAttempts = 0;
            this.emit('connected');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket 已断开', event.code);
            this.emit('disconnected');
            this.reconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket 错误', error);
            this.emit('error', error);
        };
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000;
            console.log(`${delay}ms 后重连...`);
            setTimeout(() => this.connect(), delay);
        }
    }
    
    send(type, data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, ...data }));
        }
    }
    
    on(type, handler) {
        if (!this.handlers.has(type)) {
            this.handlers.set(type, []);
        }
        this.handlers.get(type).push(handler);
    }
    
    emit(type, data) {
        const handlers = this.handlers.get(type) || [];
        handlers.forEach(handler => handler(data));
    }
    
    handleMessage(data) {
        const type = data.type;
        this.emit(type, data);
        this.emit('message', data);
    }
    
    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 使用示例
const ws = new WebSocketClient('wss://api.example.com/ws', 'your-jwt-token');

ws.on('connected', () => {
    console.log('已连接');
    ws.send('join_room', { room: 'general' });
});

ws.on('chat', (data) => {
    console.log(`收到消息: ${data.from}: ${data.content}`);
});

ws.on('notification', (data) => {
    showNotification(data.title, data.body);
});

ws.connect();

// 发送消息
ws.send('chat', {
    to: 'user123',
    content: '你好！'
});
```

### Python 客户端

```python
import asyncio
import websockets
import json

class WebSocketClient:
    def __init__(self, url: str, token: str):
        self.url = f"{url}?token={token}"
        self.ws = None
        self.handlers = {}
    
    def on(self, message_type: str):
        def decorator(func):
            self.handlers[message_type] = func
            return func
        return decorator
    
    async def connect(self):
        async with websockets.connect(self.url) as ws:
            self.ws = ws
            await self._listen()
    
    async def _listen(self):
        async for message in self.ws:
            data = json.loads(message)
            await self._handle_message(data)
    
    async def _handle_message(self, data: dict):
        message_type = data.get("type")
        handler = self.handlers.get(message_type)
        if handler:
            await handler(data)
    
    async def send(self, message_type: str, data: dict):
        await self.ws.send(json.dumps({
            "type": message_type,
            **data
        }))

# 使用示例
client = WebSocketClient("wss://api.example.com/ws", "your-token")

@client.on("chat")
async def handle_chat(data):
    print(f"收到消息: {data['content']}")

@client.on("notification")
async def handle_notification(data):
    print(f"通知: {data['title']}")

asyncio.run(client.connect())
```

---

## 注意事项

1. **连接管理**: 注意处理连接断开和重连逻辑
2. **消息格式**: 使用统一的 JSON 消息格式
3. **认证安全**: 通过查询参数或首条消息传递令牌
4. **心跳机制**: 实现心跳检测避免连接超时
5. **错误处理**: 正确处理各种异常情况
6. **资源清理**: 连接断开时清理相关资源
7. **限流保护**: 对消息发送频率进行限制
