# Cookiecutter FastAPI 基础模板

一个功能完备、生产就绪的 FastAPI 项目模板，采用现代化最佳实践构建。

---

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置选项](#配置选项)
- [项目结构](#项目结构)
- [核心功能详解](#核心功能详解)
- [开发指南](#开发指南)

---

## 功能特性

### 核心框架

| 功能 | 说明 |
|------|------|
| **FastAPI** | 高性能异步 Web 框架，自动生成 OpenAPI 文档 |
| **SQLAlchemy 2.0** | 现代化异步 ORM，完整类型注解支持 |
| **Pydantic v2** | 数据验证和序列化，性能大幅提升 |
| **Alembic** | 数据库版本控制和迁移管理 |

### 安全认证

| 功能 | 说明 |
|------|------|
| **JWT 认证** | 无状态令牌认证，支持访问令牌和刷新令牌 |
| **RBAC** | 基于角色的访问控制，细粒度权限管理 |
| **密码哈希** | 使用 bcrypt 算法安全存储密码 |

### 业务服务

| 服务 | 说明 |
|------|------|
| **邮件服务** | 异步邮件发送，HTML 模板、附件支持 |
| **文件服务** | 文件上传存储，类型验证、大小限制 |
| **缓存服务** | Redis 缓存封装，装饰器缓存、分布式锁 |
| **审计服务** | 操作日志记录，安全审计支持 |

### 异常处理

| 功能 | 说明 |
|------|------|
| **全局异常处理器** | 统一的错误响应格式 |
| **自定义异常类** | 业务异常、验证异常、认证异常等 |

### 事件系统

| 功能 | 说明 |
|------|------|
| **事件总线** | 发布/订阅模式，解耦业务逻辑 |
| **事件装饰器** | 简化事件订阅和处理 |

### 工具集

| 工具 | 说明 |
|------|------|
| **分页工具** | 偏移分页和游标分页支持 |
| **验证器** | 邮箱、手机号、身份证、密码强度等 |
| **结构化日志** | JSON 格式日志，请求上下文支持 |

### 中间件

| 中间件 | 说明 |
|------|------|
| **请求日志** | 记录请求详细信息 |
| **CORS** | 跨域资源共享配置 |
| **限流** | 基于 IP 的请求限流 |
| **请求 ID** | 为每个请求生成唯一标识 |

### 可选功能

| 功能 | 说明 |
|------|------|
| **WebSocket** | 实时通信，连接管理、房间、广播 |
| **Jinja2 模板** | 服务端渲染支持 |
| **Redis** | 缓存、会话存储、分布式锁 |
| **Celery** | 分布式任务队列和定时任务 |
| **Docker** | 多阶段构建，生产就绪 |

---

## 环境要求

- Python 3.11+
- cookiecutter

## 快速开始

### 安装 Cookiecutter

```bash
pip install cookiecutter
```

### 生成项目

```bash
# 从 GitHub 生成
cookiecutter https://github.com/yourusername/cookiecutter-fastapi-base

# 从本地目录生成
cookiecutter path/to/cookiecutter-fastapi-base
```

### 交互式配置

生成时会提示你输入以下配置：

```
project_name [我的 FastAPI 项目]: 
# 项目名称，可以使用中文

project_slug [my_fastapi_project]: 
# 项目目录名，Python 包名

project_description [一个生产级别的 FastAPI 项目]: 
# 项目描述

author_name [您的姓名]: 
# 作者姓名

author_email [your.email@example.com]: 
# 作者邮箱

version [0.1.0]: 
# 初始版本号

python_version [3.11]: 
# Python 版本

database_type [postgresql]: 
# 数据库类型：postgresql/mysql/sqlite

use_redis [yes]: 
# 是否启用 Redis

use_celery [yes]: 
# 是否启用 Celery

include_websocket [yes]: 
# 是否启用 WebSocket

include_jinja2 [yes]: 
# 是否启用 Jinja2 模板
```

---

## 配置选项

### 基本配置

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `project_name` | 我的 FastAPI 项目 | 项目名称（支持中文） |
| `project_slug` | 自动生成 | Python 包名，目录名 |
| `project_description` | 一个生产级别的 FastAPI 项目 | 项目简介 |
| `author_name` | 您的姓名 | 作者姓名 |
| `author_email` | your.email@example.com | 作者邮箱 |
| `version` | 0.1.0 | 初始版本号 |

### 技术配置

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `python_version` | 3.11 | Python 版本（3.10+ 推荐） |
| `database_type` | postgresql | 数据库类型：postgresql/mysql/sqlite |

### 可选功能

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `use_redis` | yes | 启用 Redis 缓存和会话存储 |
| `use_celery` | yes | 启用 Celery 异步任务队列 |
| `include_websocket` | yes | 启用 WebSocket 实时通信 |
| `include_jinja2` | yes | 启用 Jinja2 模板引擎 |

---

## 项目结构

生成的项目结构如下：

```
your_project/
├── app/
│   ├── api/                        # API 路由和端点
│   │   ├── v1/                     # API 版本 1
│   │   │   ├── endpoints/          # 各端点处理器
│   │   │   │   ├── auth.py         # 认证端点
│   │   │   │   ├── users.py        # 用户管理
│   │   │   │   ├── roles.py        # 角色管理
│   │   │   │   ├── files.py        # 文件管理
│   │   │   │   └── health.py       # 健康检查
│   │   │   └── router.py           # 路由聚合
│   │   └── deps.py                 # 依赖注入
│   ├── core/                       # 核心应用模块
│   │   ├── config.py               # Pydantic 配置
│   │   ├── security.py             # JWT 和密码哈希
│   │   ├── rbac.py                 # 基于角色的访问控制
│   │   ├── exceptions.py           # 自定义异常
│   │   ├── exception_handlers.py   # 异常处理器
│   │   ├── events.py               # 事件系统
│   │   └── celery_app.py           # Celery 配置
│   ├── db/                         # 数据库层
│   │   ├── base.py                 # SQLAlchemy 基础模型
│   │   ├── session.py              # 异步会话管理
│   │   └── repositories/           # 仓储模式
│   │       └── base.py             # 基础仓储类
│   ├── models/                     # SQLAlchemy ORM 模型
│   │   ├── user.py                 # 用户模型
│   │   ├── role.py                 # 角色模型
│   │   └── audit_log.py            # 审计日志模型
│   ├── schemas/                    # Pydantic 模式
│   │   ├── user.py                 # 用户模式
│   │   ├── role.py                 # 角色模式
│   │   ├── auth.py                 # 认证模式
│   │   └── common.py               # 通用模式
│   ├── services/                   # 业务逻辑服务层
│   │   ├── base.py                 # 基础服务类
│   │   ├── user.py                 # 用户服务
│   │   ├── auth.py                 # 认证服务
│   │   ├── email.py                # 邮件服务
│   │   ├── file.py                 # 文件服务
│   │   ├── cache.py                # 缓存服务
│   │   └── audit.py                # 审计服务
│   ├── tasks/                      # Celery 异步任务
│   │   ├── email.py                # 邮件任务
│   │   └── maintenance.py          # 维护任务
│   ├── middleware/                 # 自定义中间件
│   │   ├── logging.py              # 请求/响应日志
│   │   ├── cors.py                 # CORS 配置
│   │   ├── rate_limit.py           # 速率限制
│   │   └── request_id.py           # 请求 ID
│   ├── websocket/                  # WebSocket 处理器
│   │   ├── manager.py              # 连接管理器
│   │   └── handlers.py             # 消息处理器
│   ├── utils/                      # 工具函数
│   │   ├── helpers.py              # 通用工具
│   │   ├── validators.py           # 数据验证器
│   │   ├── pagination.py           # 分页工具
│   │   └── logging.py              # 日志工具
│   ├── templates/                  # Jinja2 模板
│   ├── static/                     # 静态文件
│   └── main.py                     # 应用入口
├── tests/                          # 测试套件
│   ├── api/                        # API 测试
│   │   ├── test_auth.py            # 认证测试
│   │   └── test_users.py           # 用户测试
│   ├── unit/                       # 单元测试
│   │   ├── test_services.py        # 服务测试
│   │   └── test_validators.py      # 验证器测试
│   └── conftest.py                 # 测试配置
├── alembic/                        # 数据库迁移
│   ├── versions/                   # 迁移版本文件
│   └── env.py                      # 迁移环境配置
├── docker/                         # Docker 配置
│   ├── Dockerfile                  # 生产 Dockerfile
│   └── Dockerfile.dev              # 开发 Dockerfile
├── requirements.txt                # 生产环境依赖
├── requirements-dev.txt            # 开发环境依赖
├── docker-compose.yml              # 生产环境 Compose
├── docker-compose.dev.yml          # 开发环境 Compose
├── pyproject.toml                  # 项目配置
├── alembic.ini                     # Alembic 配置
└── .env.example                    # 环境变量模板
```

---

## 核心功能详解

### RBAC 权限系统

项目实现了完整的基于角色的访问控制：

- **权限定义**：细粒度的操作权限（读、写、删除等）
- **角色管理**：角色与权限的映射
- **权限继承**：支持角色层级和权限继承
- **依赖注入**：通过 FastAPI 依赖进行权限检查

### 事件驱动架构

内置的事件系统支持：

- **发布/订阅模式**：解耦业务逻辑
- **事件优先级**：控制处理顺序
- **异步处理**：支持异步事件处理器
- **预定义事件**：用户创建、登录、文件上传等

### 全局异常处理

统一的异常处理机制：

- **统一响应格式**：所有错误返回相同结构
- **自定义异常类**：业务异常、验证异常、认证异常等
- **自动日志**：自动记录错误信息
- **调试支持**：开发环境返回详细堆栈

### 仓储模式

类型安全的数据库操作：

- **泛型支持**：基于泛型的仓储基类
- **CRUD 操作**：通用的增删改查方法
- **分页支持**：内置分页和排序
- **过滤器**：灵活的查询条件构建

---

## 开发指南

### 生成项目后

1. **创建虚拟环境**
   ```bash
   cd your_project
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # 开发依赖
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件配置数据库等
   ```

4. **运行数据库迁移**
   ```bash
   alembic upgrade head
   ```

5. **启动开发服务器**
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker 开发

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up --build

# 生产环境
docker-compose up --build -d
```

### 访问 API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 运行测试

```bash
# 运行所有测试
pytest

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

---

## 最佳实践

- 选择适合项目的可选功能，避免不必要的复杂性
- 修改 `SECRET_KEY` 为安全的随机字符串
- 生产环境设置 `DEBUG=false`
- 配置适当的日志级别
- 定期更新依赖包

---

## 许可证

MIT 许可证

## 贡献

欢迎提交 Issue 和 Pull Request！
