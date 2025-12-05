# 数据模型模块 (Models)

本模块定义 SQLAlchemy ORM 数据模型，映射数据库表结构。

## 目录

- [模块结构](#模块结构)
- [用户模型](#用户模型)
- [角色模型](#角色模型)
- [审计日志模型](#审计日志模型)
- [模型关系](#模型关系)
- [自定义模型](#自定义模型)
- [模型混入类](#模型混入类)

---

## 模块结构

```
models/
├── __init__.py      # 模型导出
├── user.py          # 用户模型
├── role.py          # 角色和用户角色关联模型
└── audit_log.py     # 审计日志模型
```

---

## 用户模型

### 文件：`user.py`

定义用户表结构和用户相关方法。

### User 模型

```python
from app.models import User

# 模型字段
class User(Base):
    __tablename__ = "users"
    
    id: int                  # 主键
    username: str            # 用户名（唯一）
    email: str               # 邮箱（唯一）
    hashed_password: str     # 密码哈希
    full_name: str | None    # 全名
    is_active: bool          # 是否激活
    is_superuser: bool       # 是否超级管理员
    avatar: str | None       # 头像 URL
    phone: str | None        # 手机号
    last_login: datetime     # 最后登录时间
    created_at: datetime     # 创建时间
    updated_at: datetime     # 更新时间
    
    # 关联关系
    roles: list[Role]        # 用户角色列表
    audit_logs: list[AuditLog]  # 操作日志
```

### 使用示例

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import User

# 创建用户
new_user = User(
    username="张三",
    email="zhangsan@example.com",
    hashed_password=SecurityManager.hash_password("password123"),
    full_name="张三",
    is_active=True
)
db.add(new_user)
await db.commit()

# 查询用户
result = await db.execute(
    select(User).where(User.username == "张三")
)
user = result.scalar_one_or_none()

# 查询用户及其角色
result = await db.execute(
    select(User)
    .options(selectinload(User.roles))
    .where(User.id == 1)
)
user = result.scalar_one()
print(user.roles)  # 用户的所有角色

# 检查用户权限
if user.is_superuser:
    print("超级管理员")

# 更新用户
user.full_name = "张三三"
user.updated_at = datetime.utcnow()
await db.commit()
```

### 模型方法

```python
class User(Base):
    # ... 字段定义 ...
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return SecurityManager.verify_password(password, self.hashed_password)
    
    def has_role(self, role_name: str) -> bool:
        """检查是否拥有指定角色"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission: str) -> bool:
        """检查是否拥有指定权限"""
        if self.is_superuser:
            return True
        for role in self.roles:
            if permission in role.permissions:
                return True
        return False
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.full_name or self.username
```

---

## 角色模型

### 文件：`role.py`

定义角色和用户角色关联表。

### Role 模型

```python
from app.models import Role, UserRole

# 角色模型
class Role(Base):
    __tablename__ = "roles"
    
    id: int                  # 主键
    name: str                # 角色名（唯一）
    display_name: str        # 显示名称
    description: str | None  # 角色描述
    permissions: list[str]   # 权限列表（JSON）
    is_system: bool          # 是否系统角色
    created_at: datetime     # 创建时间
    updated_at: datetime     # 更新时间
    
    # 关联关系
    users: list[User]        # 拥有此角色的用户
```

### UserRole 关联模型

```python
# 用户角色关联表（多对多）
class UserRole(Base):
    __tablename__ = "user_roles"
    
    id: int           # 主键
    user_id: int      # 用户ID（外键）
    role_id: int      # 角色ID（外键）
    created_at: datetime  # 分配时间
    created_by: int   # 分配人ID
```

### 使用示例

```python
from app.models import Role, UserRole

# 创建角色
admin_role = Role(
    name="admin",
    display_name="管理员",
    description="系统管理员，拥有所有权限",
    permissions=["user:read", "user:write", "user:delete", "role:manage"],
    is_system=True
)
db.add(admin_role)
await db.commit()

# 分配角色给用户
user_role = UserRole(
    user_id=1,
    role_id=admin_role.id,
    created_by=current_user.id
)
db.add(user_role)
await db.commit()

# 查询角色及其用户
result = await db.execute(
    select(Role)
    .options(selectinload(Role.users))
    .where(Role.name == "admin")
)
role = result.scalar_one()
print(f"管理员用户数: {len(role.users)}")

# 检查角色权限
if "user:delete" in role.permissions:
    print("角色可删除用户")
```

### 预定义角色

```python
# 系统预定义角色
SYSTEM_ROLES = [
    {
        "name": "admin",
        "display_name": "管理员",
        "permissions": ["*"],  # 所有权限
        "is_system": True
    },
    {
        "name": "user",
        "display_name": "普通用户",
        "permissions": ["user:read", "profile:update"],
        "is_system": True
    },
    {
        "name": "moderator",
        "display_name": "审核员",
        "permissions": ["user:read", "content:review", "content:delete"],
        "is_system": True
    }
]
```

---

## 审计日志模型

### 文件：`audit_log.py`

记录用户操作日志，用于审计追踪。

### AuditLog 模型

```python
from app.models import AuditLog

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: int                  # 主键
    user_id: int | None      # 操作用户ID
    action: str              # 操作类型
    resource_type: str       # 资源类型
    resource_id: str | None  # 资源ID
    old_value: dict | None   # 变更前的值（JSON）
    new_value: dict | None   # 变更后的值（JSON）
    ip_address: str | None   # IP 地址
    user_agent: str | None   # User-Agent
    request_id: str | None   # 请求ID
    status: str              # 操作状态（success/failed）
    error_message: str | None # 错误信息
    created_at: datetime     # 操作时间
    
    # 关联关系
    user: User | None        # 操作用户
```

### 使用示例

```python
from app.models import AuditLog

# 记录操作日志
audit_log = AuditLog(
    user_id=current_user.id,
    action="user.update",
    resource_type="user",
    resource_id=str(target_user.id),
    old_value={"email": "old@example.com"},
    new_value={"email": "new@example.com"},
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    status="success"
)
db.add(audit_log)
await db.commit()

# 查询用户操作日志
result = await db.execute(
    select(AuditLog)
    .where(AuditLog.user_id == user_id)
    .order_by(AuditLog.created_at.desc())
    .limit(50)
)
logs = result.scalars().all()

# 查询资源变更历史
result = await db.execute(
    select(AuditLog)
    .where(
        AuditLog.resource_type == "user",
        AuditLog.resource_id == "123"
    )
    .order_by(AuditLog.created_at.desc())
)
history = result.scalars().all()
```

### 操作类型枚举

```python
class AuditAction:
    """审计操作类型"""
    # 用户相关
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_PASSWORD_CHANGE = "user.password_change"
    
    # 角色相关
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    ROLE_ASSIGN = "role.assign"
    ROLE_REVOKE = "role.revoke"
    
    # 系统相关
    SYSTEM_CONFIG_CHANGE = "system.config_change"
    SYSTEM_BACKUP = "system.backup"
```

---

## 模型关系

### 关系图

```
┌───────────┐       ┌────────────┐       ┌───────────┐
│   User    │◄──────│  UserRole  │──────►│   Role    │
└───────────┘       └────────────┘       └───────────┘
      │
      │ 1:N
      ▼
┌───────────┐
│ AuditLog  │
└───────────┘
```

### 定义关联关系

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    
    # 多对多关系：用户 <-> 角色
    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin"  # 默认预加载
    )
    
    # 一对多关系：用户 -> 审计日志
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )

class Role(Base):
    __tablename__ = "roles"
    
    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles"
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user = relationship("User", back_populates="audit_logs")
```

---

## 自定义模型

### 创建新模型

```python
# models/article.py
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db import Base

class Article(Base):
    """文章模型"""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="文章标题")
    slug = Column(String(200), unique=True, index=True, comment="URL 别名")
    content = Column(Text, comment="文章内容")
    summary = Column(String(500), comment="文章摘要")
    cover_image = Column(String(500), comment="封面图片")
    view_count = Column(Integer, default=0, comment="浏览次数")
    is_published = Column(Boolean, default=False, comment="是否发布")
    published_at = Column(DateTime, nullable=True, comment="发布时间")
    
    # 外键
    author_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="作者ID"
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="分类ID"
    )
    
    # 关系
    author = relationship("User", back_populates="articles")
    category = relationship("Category", back_populates="articles")
    tags = relationship("Tag", secondary="article_tags", back_populates="articles")
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("ix_articles_author_published", "author_id", "is_published"),
        {"comment": "文章表"}
    )
    
    def publish(self):
        """发布文章"""
        self.is_published = True
        self.published_at = datetime.utcnow()
    
    def increment_view(self):
        """增加浏览次数"""
        self.view_count += 1
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}')>"
```

### 注册新模型

```python
# models/__init__.py
from app.models.user import User
from app.models.role import Role, UserRole
from app.models.audit_log import AuditLog
from app.models.article import Article  # 添加新模型

__all__ = [
    "User",
    "Role",
    "UserRole",
    "AuditLog",
    "Article",
]
```

---

## 模型混入类

### 时间戳混入

```python
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

class Article(Base, TimestampMixin):
    __tablename__ = "articles"
    # created_at 和 updated_at 自动继承
```

### 软删除混入

```python
class SoftDeleteMixin:
    """软删除混入类"""
    is_deleted = Column(Boolean, default=False, comment="是否已删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    deleted_by = Column(Integer, nullable=True, comment="删除人ID")
    
    def soft_delete(self, user_id: int = None):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
    
    def restore(self):
        """恢复"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None

class Article(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "articles"
    # 同时具有时间戳和软删除功能
```

### 审计混入

```python
class AuditMixin:
    """审计混入类"""
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    updated_by = Column(Integer, nullable=True, comment="更新人ID")
    
    def set_creator(self, user_id: int):
        """设置创建人"""
        self.created_by = user_id
        self.updated_by = user_id
    
    def set_updater(self, user_id: int):
        """设置更新人"""
        self.updated_by = user_id
```

---

## 注意事项

1. **表名命名**: 使用小写复数形式，如 `users`, `articles`
2. **字段命名**: 使用小写下划线形式，如 `created_at`, `user_id`
3. **索引优化**: 为常用查询字段添加索引
4. **外键约束**: 明确定义外键的删除行为（CASCADE/SET NULL/RESTRICT）
5. **关系加载**: 根据使用场景选择合适的加载策略（lazy/selectin/joined）
6. **模型方法**: 将业务逻辑封装在模型方法中
7. **注释文档**: 使用 `comment` 参数添加字段说明
