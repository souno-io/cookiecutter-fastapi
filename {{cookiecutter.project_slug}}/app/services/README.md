# 服务层模块 (Services)

本模块提供业务逻辑层服务，封装数据访问和业务规则。

## 目录

- [模块结构](#模块结构)
- [基础服务](#基础服务)
- [用户服务](#用户服务)
- [认证服务](#认证服务)
- [邮件服务](#邮件服务)
- [文件服务](#文件服务)
- [缓存服务](#缓存服务)
- [审计服务](#审计服务)
- [自定义服务](#自定义服务)

---

## 模块结构

```
services/
├── __init__.py      # 模块导出
├── base.py          # 基础服务类
├── user.py          # 用户服务
├── auth.py          # 认证服务
├── email.py         # 邮件服务
├── file.py          # 文件服务
├── cache.py         # 缓存服务
└── audit.py         # 审计日志服务
```

---

## 基础服务

### 文件：`base.py`

提供通用服务基类，封装常用的 CRUD 操作。

### BaseService 类

```python
from app.services import BaseService
from app.models import Article
from app.schemas import ArticleCreate, ArticleUpdate

class ArticleService(BaseService[Article, ArticleCreate, ArticleUpdate]):
    """文章服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Article, db)
    
    # 继承的方法：
    # get(id) -> Article | None
    # get_multi(skip, limit) -> list[Article]
    # create(obj_in: ArticleCreate) -> Article
    # update(db_obj: Article, obj_in: ArticleUpdate) -> Article
    # delete(db_obj: Article) -> None
    
    # 自定义方法
    async def get_published(self) -> list[Article]:
        """获取已发布的文章"""
        result = await self.db.execute(
            select(Article)
            .where(Article.is_published == True)
            .order_by(Article.published_at.desc())
        )
        return result.scalars().all()
```

### 使用示例

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import BaseService
from app.models import Product
from app.schemas import ProductCreate

# 在路由中使用
@router.get("/products")
async def list_products(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Product, db)
    return await service.get_multi(skip=skip, limit=limit)

# 创建记录
@router.post("/products")
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Product, db)
    return await service.create(product)
```

---

## 用户服务

### 文件：`user.py`

提供用户相关的业务逻辑。

### UserService 类

```python
from app.services import UserService

class UserService:
    """用户服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # 查询方法
    async def get(self, user_id: int) -> User | None
    async def get_by_email(self, email: str) -> User | None
    async def get_by_username(self, username: str) -> User | None
    async def get_multi(self, skip: int, limit: int) -> list[User]
    
    # 创建/更新方法
    async def create(self, obj_in: UserCreate) -> User
    async def update(self, user: User, obj_in: UserUpdate) -> User
    async def update_password(self, user: User, new_password: str) -> User
    
    # 状态管理
    async def activate(self, user: User) -> User
    async def deactivate(self, user: User) -> User
    
    # 角色管理
    async def assign_role(self, user_id: int, role_id: int) -> None
    async def remove_role(self, user_id: int, role_id: int) -> None
```

### 使用示例

```python
from app.services import UserService
from app.schemas import UserCreate, UserUpdate

# 创建用户
async def register_user(db: AsyncSession, data: UserCreate) -> User:
    service = UserService(db)
    
    # 检查用户名是否存在
    if await service.get_by_username(data.username):
        raise ConflictError("用户名已存在")
    
    # 检查邮箱是否存在
    if await service.get_by_email(data.email):
        raise ConflictError("邮箱已注册")
    
    # 创建用户
    return await service.create(data)

# 更新用户
async def update_profile(
    db: AsyncSession,
    user: User,
    data: UserUpdate
) -> User:
    service = UserService(db)
    return await service.update(user, data)

# 修改密码
async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str
) -> bool:
    if not SecurityManager.verify_password(current_password, user.hashed_password):
        raise AuthenticationError("当前密码错误")
    
    service = UserService(db)
    await service.update_password(user, new_password)
    return True
```

---

## 认证服务

### 文件：`auth.py`

提供用户认证和令牌管理功能。

### AuthService 类

```python
from app.services import AuthService

class AuthService:
    """认证服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # 认证方法
    async def authenticate(
        self,
        username: str,
        password: str
    ) -> User | None
    
    # 令牌管理
    def create_tokens(self, user: User) -> Token
    async def refresh_tokens(self, refresh_token: str) -> Token
    async def revoke_token(self, token: str) -> None
    
    # 密码重置
    async def request_password_reset(self, email: str) -> str
    async def reset_password(self, token: str, new_password: str) -> bool
```

### 使用示例

```python
from app.services import AuthService
from app.schemas import Token, LoginRequest

# 用户登录
@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    
    # 验证用户
    user = await auth_service.authenticate(
        credentials.username,
        credentials.password
    )
    
    if not user:
        raise AuthenticationError("用户名或密码错误")
    
    if not user.is_active:
        raise AuthenticationError("账户已被禁用")
    
    # 生成令牌
    return auth_service.create_tokens(user)

# 刷新令牌
@router.post("/refresh", response_model=Token)
async def refresh(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    return await auth_service.refresh_tokens(refresh_token)

# 密码重置流程
@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    reset_token = await auth_service.request_password_reset(email)
    
    # 发送重置邮件
    await email_service.send_password_reset(email, reset_token)
    
    return {"message": "重置链接已发送到您的邮箱"}
```

---

## 邮件服务

### 文件：`email.py`

提供邮件发送功能，支持 HTML 模板和附件。

### EmailService 类

```python
from app.services import EmailService, email_service, EmailTemplates

class EmailService:
    """邮件服务类"""
    
    # 发送邮件
    async def send(self, message: EmailMessage) -> bool
    
    # 简便方法
    async def send_simple(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html_body: str = None
    ) -> bool
    
    # 发送带附件的邮件
    async def send_with_attachment(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[tuple[str, bytes, str]]  # (文件名, 内容, MIME类型)
    ) -> bool
```

### EmailTemplates 类

```python
class EmailTemplates:
    """预定义邮件模板"""
    
    @staticmethod
    def welcome_email(username: str, login_url: str) -> tuple[str, str]:
        """欢迎邮件模板，返回 (subject, html_body)"""
    
    @staticmethod
    def password_reset_email(
        username: str,
        reset_url: str,
        expires_in: int = 30
    ) -> tuple[str, str]:
        """密码重置邮件模板"""
    
    @staticmethod
    def verification_email(
        username: str,
        verify_url: str
    ) -> tuple[str, str]:
        """邮箱验证邮件模板"""
```

### 使用示例

```python
from app.services import email_service, EmailTemplates

# 发送简单邮件
await email_service.send_simple(
    to="user@example.com",
    subject="通知",
    body="这是一封测试邮件"
)

# 发送欢迎邮件
subject, html = EmailTemplates.welcome_email(
    username="张三",
    login_url="https://example.com/login"
)
await email_service.send_simple(
    to="user@example.com",
    subject=subject,
    body="",
    html_body=html
)

# 发送密码重置邮件
subject, html = EmailTemplates.password_reset_email(
    username="张三",
    reset_url="https://example.com/reset?token=xxx",
    expires_in=30
)
await email_service.send_simple(
    to="user@example.com",
    subject=subject,
    body="",
    html_body=html
)

# 发送带附件的邮件
with open("report.pdf", "rb") as f:
    pdf_content = f.read()

await email_service.send_with_attachment(
    to="user@example.com",
    subject="月度报告",
    body="请查收附件中的月度报告",
    attachments=[("report.pdf", pdf_content, "application/pdf")]
)
```

### 配置

```bash
# .env 文件
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
SMTP_FROM_NAME=我的应用
SMTP_FROM_EMAIL=noreply@example.com
SMTP_TLS=true
```

---

## 文件服务

### 文件：`file.py`

提供文件上传、下载和管理功能。

### FileService 类

```python
from app.services import FileService, file_service

class FileService:
    """文件服务类"""
    
    # 上传文件
    async def upload(
        self,
        file: UploadFile,
        folder: str = "uploads",
        allowed_types: list[str] = None,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        rename: bool = True
    ) -> FileInfo
    
    # 上传图片（带验证和处理）
    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "images",
        max_size: int = 5 * 1024 * 1024,  # 5MB
        resize: tuple[int, int] = None  # (width, height)
    ) -> FileInfo
    
    # 删除文件
    async def delete(self, filepath: str) -> bool
    
    # 获取文件信息
    async def get_info(self, filepath: str) -> FileInfo | None
    
    # 列出目录文件
    async def list_files(
        self,
        folder: str,
        pattern: str = "*"
    ) -> list[FileInfo]
```

### FileInfo 模型

```python
class FileInfo(BaseModel):
    """文件信息"""
    filename: str           # 文件名
    original_filename: str  # 原始文件名
    filepath: str          # 相对路径
    url: str               # 访问 URL
    size: int              # 文件大小（字节）
    content_type: str      # MIME 类型
    created_at: datetime   # 上传时间
```

### 使用示例

```python
from fastapi import UploadFile, File
from app.services import file_service

# 上传文件
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(..., description="上传的文件")
):
    file_info = await file_service.upload(
        file,
        folder="documents",
        allowed_types=["pdf", "doc", "docx"],
        max_size=20 * 1024 * 1024  # 20MB
    )
    return file_info

# 上传头像
@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    file_info = await file_service.upload_image(
        file,
        folder=f"avatars/{current_user.id}",
        max_size=2 * 1024 * 1024,  # 2MB
        resize=(200, 200)
    )
    
    # 更新用户头像
    current_user.avatar = file_info.url
    await db.commit()
    
    return file_info

# 删除文件
@router.delete("/files/{filename}")
async def delete_file(filename: str):
    success = await file_service.delete(f"uploads/{filename}")
    if not success:
        raise NotFoundError("文件不存在")
    return {"message": "删除成功"}
```

### 配置

```bash
# .env 文件
UPLOAD_DIR=./uploads
UPLOAD_MAX_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,pdf,doc,docx
STATIC_URL=/static
```

---

## 缓存服务

### 文件：`cache.py`

提供 Redis 缓存功能，包括装饰器和分布式锁。

### CacheService 类

```python
from app.services import CacheService, cache_service, cached

class CacheService:
    """缓存服务类"""
    
    # 基础操作
    async def get(self, key: str) -> str | None
    async def get_json(self, key: str) -> dict | None
    async def get_model(self, key: str, model: Type[T]) -> T | None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 300  # 秒
    ) -> bool
    
    async def delete(self, key: str) -> bool
    async def exists(self, key: str) -> bool
    
    # 批量操作
    async def mget(self, keys: list[str]) -> list[str | None]
    async def mset(self, mapping: dict[str, Any], expire: int = 300) -> bool
    async def delete_pattern(self, pattern: str) -> int
    
    # 分布式锁
    async def acquire_lock(
        self,
        name: str,
        timeout: int = 10,
        blocking: bool = True
    ) -> str | None  # 返回锁 token
    
    async def release_lock(self, name: str, token: str) -> bool
    
    # 计数器
    async def incr(self, key: str, amount: int = 1) -> int
    async def decr(self, key: str, amount: int = 1) -> int
```

### cached 装饰器

```python
from app.services import cached

# 缓存函数结果
@cached(expire=300, prefix="user")
async def get_user(user_id: int) -> User:
    """获取用户，结果缓存5分钟"""
    return await db.get(User, user_id)

# 缓存键会自动生成为: user:get_user:user_id=1

# 自定义缓存键
@cached(expire=600, key="article:{article_id}")
async def get_article(article_id: int) -> Article:
    return await db.get(Article, article_id)

# 条件缓存
@cached(expire=300, condition=lambda r: r is not None)
async def get_optional_data(key: str) -> dict | None:
    """只在结果不为 None 时缓存"""
    return await fetch_data(key)
```

### 使用示例

```python
from app.services import cache_service

# 缓存查询结果
async def get_user_with_cache(user_id: int) -> User | None:
    cache_key = f"user:{user_id}"
    
    # 尝试从缓存获取
    cached_user = await cache_service.get_model(cache_key, User)
    if cached_user:
        return cached_user
    
    # 查询数据库
    user = await db.get(User, user_id)
    if user:
        # 写入缓存
        await cache_service.set(cache_key, user.model_dump(), expire=300)
    
    return user

# 使用分布式锁
async def process_order(order_id: int):
    lock_name = f"order:{order_id}"
    
    # 获取锁
    token = await cache_service.acquire_lock(lock_name, timeout=30)
    if not token:
        raise BusinessError("订单正在处理中，请稍后重试")
    
    try:
        # 处理订单逻辑
        await do_process_order(order_id)
    finally:
        # 释放锁
        await cache_service.release_lock(lock_name, token)

# 计数器
async def increment_view_count(article_id: int) -> int:
    return await cache_service.incr(f"views:{article_id}")

# 清除缓存
async def invalidate_user_cache(user_id: int):
    await cache_service.delete(f"user:{user_id}")
    await cache_service.delete_pattern(f"user:{user_id}:*")
```

---

## 审计服务

### 文件：`audit.py`

提供操作审计日志功能。

### AuditLogService 类

```python
from app.services import AuditLogService, audit_service, AuditAction

class AuditLogService:
    """审计日志服务"""
    
    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str = None,
        user_id: int = None,
        old_value: dict = None,
        new_value: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        request_id: str = None,
        status: str = "success",
        error_message: str = None
    ) -> AuditLog
    
    @staticmethod
    async def get_logs(
        db: AsyncSession,
        user_id: int = None,
        action: str = None,
        resource_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLog]
```

### AuditAction 枚举

```python
class AuditAction:
    """审计操作类型"""
    # 用户操作
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_PASSWORD_CHANGE = "user.password_change"
    
    # 角色操作
    ROLE_CREATE = "role.create"
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"
    
    # 数据操作
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
```

### 使用示例

```python
from app.services import audit_service, AuditAction

# 记录用户登录
await audit_service.log(
    db=db,
    action=AuditAction.USER_LOGIN,
    resource_type="user",
    resource_id=str(user.id),
    user_id=user.id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)

# 记录数据修改
old_data = user.model_dump()
user.email = "new@example.com"
await db.commit()

await audit_service.log(
    db=db,
    action=AuditAction.USER_UPDATE,
    resource_type="user",
    resource_id=str(user.id),
    user_id=current_user.id,
    old_value={"email": old_data["email"]},
    new_value={"email": user.email}
)

# 查询审计日志
logs = await audit_service.get_logs(
    db=db,
    user_id=user_id,
    start_date=datetime.now() - timedelta(days=7),
    limit=50
)
```

---

## 自定义服务

### 创建新服务

```python
# services/order.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Order, OrderItem
from app.schemas import OrderCreate
from app.services import BaseService
from app.core.events import event_bus, OrderCreatedEvent

class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    """订单服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Order, db)
    
    async def create_order(
        self,
        user_id: int,
        items: list[dict],
        address: str
    ) -> Order:
        """创建订单"""
        # 计算总金额
        total = sum(item["price"] * item["quantity"] for item in items)
        
        # 创建订单
        order = Order(
            user_id=user_id,
            total_amount=total,
            shipping_address=address,
            status="pending"
        )
        self.db.add(order)
        await self.db.flush()
        
        # 创建订单项
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                price=item["price"]
            )
            self.db.add(order_item)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # 发布订单创建事件
        await event_bus.publish(OrderCreatedEvent(
            order_id=order.id,
            user_id=user_id,
            total_amount=total
        ))
        
        return order
    
    async def pay_order(self, order_id: int) -> Order:
        """支付订单"""
        order = await self.get(order_id)
        if not order:
            raise NotFoundError("订单不存在")
        
        if order.status != "pending":
            raise BusinessError("订单状态不允许支付")
        
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        await self.db.commit()
        
        return order
    
    async def get_user_orders(
        self,
        user_id: int,
        status: str = None
    ) -> list[Order]:
        """获取用户订单"""
        query = select(Order).where(Order.user_id == user_id)
        if status:
            query = query.where(Order.status == status)
        query = query.order_by(Order.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
```

### 注册服务

```python
# services/__init__.py
from app.services.order import OrderService

__all__ = [
    # ... 其他服务
    "OrderService",
]
```

---

## 注意事项

1. **依赖注入**: 服务类应通过构造函数接收数据库会话
2. **事务管理**: 复杂操作应在服务层管理事务
3. **异常处理**: 使用自定义异常，不要在服务层处理 HTTP 响应
4. **解耦设计**: 使用事件系统解耦跨服务的业务逻辑
5. **缓存策略**: 合理使用缓存，注意缓存失效
6. **日志记录**: 重要操作应记录审计日志
7. **单元测试**: 为服务层编写独立的单元测试
