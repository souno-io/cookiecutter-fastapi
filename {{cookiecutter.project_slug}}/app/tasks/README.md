# 异步任务模块 (Tasks)

本模块提供 Celery 异步任务定义，用于处理耗时操作和定时任务。

## 目录

- [模块结构](#模块结构)
- [Celery 配置](#celery-配置)
- [邮件任务](#邮件任务)
- [维护任务](#维护任务)
- [自定义任务](#自定义任务)
- [定时任务](#定时任务)
- [任务监控](#任务监控)
- [最佳实践](#最佳实践)

---

## 模块结构

```
tasks/
├── __init__.py          # 模块导出
├── email.py             # 邮件发送任务
└── maintenance.py       # 系统维护任务
```

---

## Celery 配置

### 配置文件

Celery 配置位于 `app/core/celery_app.py`。

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,      # Redis: redis://localhost:6379/0
    backend=settings.CELERY_RESULT_BACKEND,  # Redis: redis://localhost:6379/1
)

# 任务配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5分钟超时
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])
```

### 环境配置

```bash
# .env 文件
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 启动 Worker

```bash
# 启动 Celery worker
celery -A app.core.celery_app worker --loglevel=info

# 指定并发数
celery -A app.core.celery_app worker --concurrency=4 --loglevel=info

# 指定队列
celery -A app.core.celery_app worker -Q default,email --loglevel=info

# 启动定时任务调度器
celery -A app.core.celery_app beat --loglevel=info

# 同时启动 worker 和 beat（开发环境）
celery -A app.core.celery_app worker --beat --loglevel=info
```

---

## 邮件任务

### 文件：`email.py`

异步发送邮件的任务定义。

### 任务定义

```python
from celery import shared_task
from app.core.celery_app import celery_app

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def send_email_task(
    self,
    to: str | list[str],
    subject: str,
    body: str,
    html_body: str = None,
    attachments: list = None
) -> dict:
    """
    异步发送邮件任务
    
    参数:
        to: 收件人邮箱（单个或列表）
        subject: 邮件主题
        body: 纯文本内容
        html_body: HTML 内容（可选）
        attachments: 附件列表（可选）
    
    返回:
        {"status": "sent", "message_id": "xxx"}
    """
    try:
        from app.services import email_service
        
        result = email_service.send_sync(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachments
        )
        
        return {
            "status": "sent",
            "to": to,
            "subject": subject
        }
        
    except Exception as exc:
        # 重试
        raise self.retry(exc=exc)
```

### 预定义邮件任务

```python
@celery_app.task
def send_welcome_email_task(user_id: int, email: str, username: str):
    """发送欢迎邮件"""
    from app.services import EmailTemplates
    
    subject, html = EmailTemplates.welcome_email(
        username=username,
        login_url="https://example.com/login"
    )
    
    return send_email_task.delay(
        to=email,
        subject=subject,
        body="",
        html_body=html
    )

@celery_app.task
def send_password_reset_email_task(email: str, username: str, reset_token: str):
    """发送密码重置邮件"""
    from app.services import EmailTemplates
    
    reset_url = f"https://example.com/reset-password?token={reset_token}"
    subject, html = EmailTemplates.password_reset_email(
        username=username,
        reset_url=reset_url,
        expires_in=30
    )
    
    return send_email_task.delay(
        to=email,
        subject=subject,
        body="",
        html_body=html
    )

@celery_app.task
def send_notification_email_task(user_ids: list[int], subject: str, content: str):
    """批量发送通知邮件"""
    from app.models import User
    from app.db import async_session_maker
    
    async def get_emails():
        async with async_session_maker() as db:
            result = await db.execute(
                select(User.email).where(User.id.in_(user_ids))
            )
            return result.scalars().all()
    
    emails = asyncio.run(get_emails())
    
    results = []
    for email in emails:
        result = send_email_task.delay(
            to=email,
            subject=subject,
            body=content
        )
        results.append(result.id)
    
    return {"sent_count": len(results), "task_ids": results}
```

### 使用示例

```python
from app.tasks.email import (
    send_email_task,
    send_welcome_email_task,
    send_password_reset_email_task,
)

# 基础邮件发送
send_email_task.delay(
    to="user@example.com",
    subject="测试邮件",
    body="这是一封测试邮件"
)

# 发送欢迎邮件
send_welcome_email_task.delay(
    user_id=1,
    email="newuser@example.com",
    username="新用户"
)

# 发送密码重置邮件
send_password_reset_email_task.delay(
    email="user@example.com",
    username="用户名",
    reset_token="abc123"
)

# 延迟发送
from datetime import timedelta
send_email_task.apply_async(
    args=["user@example.com", "定时邮件", "这是定时发送的邮件"],
    countdown=60  # 60秒后发送
)

# 指定时间发送
from datetime import datetime
send_email_task.apply_async(
    args=["user@example.com", "定时邮件", "这是定时发送的邮件"],
    eta=datetime(2024, 1, 1, 9, 0, 0)  # 指定时间发送
)
```

---

## 维护任务

### 文件：`maintenance.py`

系统维护和清理任务。

### 任务定义

```python
from celery import shared_task
from app.core.celery_app import celery_app
from datetime import datetime, timedelta

@celery_app.task
def cleanup_expired_tokens():
    """清理过期的令牌"""
    from app.db import async_session_maker
    from app.models import Token
    
    async def cleanup():
        async with async_session_maker() as db:
            result = await db.execute(
                delete(Token).where(Token.expires_at < datetime.utcnow())
            )
            await db.commit()
            return result.rowcount
    
    import asyncio
    deleted = asyncio.run(cleanup())
    
    return {"deleted_tokens": deleted}

@celery_app.task
def cleanup_old_audit_logs(days: int = 90):
    """清理旧的审计日志"""
    from app.db import async_session_maker
    from app.models import AuditLog
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    async def cleanup():
        async with async_session_maker() as db:
            result = await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff_date)
            )
            await db.commit()
            return result.rowcount
    
    import asyncio
    deleted = asyncio.run(cleanup())
    
    return {"deleted_logs": deleted, "before_date": cutoff_date.isoformat()}

@celery_app.task
def cleanup_temp_files():
    """清理临时文件"""
    import os
    import shutil
    from pathlib import Path
    
    temp_dir = Path("./uploads/temp")
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    deleted_count = 0
    deleted_size = 0
    
    for file_path in temp_dir.glob("*"):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff_time:
                deleted_size += file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
    
    return {
        "deleted_files": deleted_count,
        "freed_space_mb": round(deleted_size / 1024 / 1024, 2)
    }

@celery_app.task
def generate_daily_report():
    """生成每日统计报告"""
    from app.db import async_session_maker
    from app.models import User, AuditLog
    from sqlalchemy import func
    
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    async def get_stats():
        async with async_session_maker() as db:
            # 新增用户数
            new_users = await db.execute(
                select(func.count(User.id)).where(
                    func.date(User.created_at) == yesterday
                )
            )
            
            # 活跃用户数
            active_users = await db.execute(
                select(func.count(func.distinct(AuditLog.user_id))).where(
                    func.date(AuditLog.created_at) == yesterday
                )
            )
            
            return {
                "date": yesterday.isoformat(),
                "new_users": new_users.scalar(),
                "active_users": active_users.scalar()
            }
    
    import asyncio
    stats = asyncio.run(get_stats())
    
    # 可以发送报告邮件
    send_email_task.delay(
        to="admin@example.com",
        subject=f"每日报告 - {stats['date']}",
        body=f"新增用户: {stats['new_users']}\n活跃用户: {stats['active_users']}"
    )
    
    return stats

@celery_app.task
def health_check():
    """健康检查任务"""
    from app.db import async_session_maker
    import redis
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # 检查数据库
    try:
        async def check_db():
            async with async_session_maker() as db:
                await db.execute(text("SELECT 1"))
        
        import asyncio
        asyncio.run(check_db())
        results["services"]["database"] = "ok"
    except Exception as e:
        results["services"]["database"] = f"error: {str(e)}"
    
    # 检查 Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        results["services"]["redis"] = "ok"
    except Exception as e:
        results["services"]["redis"] = f"error: {str(e)}"
    
    return results
```

---

## 自定义任务

### 创建新任务

```python
# tasks/data_processing.py
from celery import shared_task
from app.core.celery_app import celery_app

@celery_app.task(
    bind=True,
    name="tasks.process_data",
    queue="data_processing",
    max_retries=3,
    default_retry_delay=300
)
def process_data_task(self, data_id: int) -> dict:
    """
    数据处理任务
    
    参数:
        data_id: 数据ID
    
    返回:
        处理结果
    """
    try:
        # 更新任务状态
        self.update_state(state="PROCESSING", meta={"progress": 0})
        
        # 获取数据
        data = get_data(data_id)
        self.update_state(state="PROCESSING", meta={"progress": 20})
        
        # 处理数据
        result = process(data)
        self.update_state(state="PROCESSING", meta={"progress": 80})
        
        # 保存结果
        save_result(result)
        self.update_state(state="PROCESSING", meta={"progress": 100})
        
        return {"status": "completed", "data_id": data_id}
        
    except Exception as exc:
        self.update_state(state="FAILED", meta={"error": str(exc)})
        raise self.retry(exc=exc)

@celery_app.task(bind=True)
def long_running_task(self, items: list) -> dict:
    """长时间运行的任务（带进度报告）"""
    total = len(items)
    processed = 0
    
    for item in items:
        # 处理单个项目
        process_item(item)
        processed += 1
        
        # 更新进度
        progress = int(processed / total * 100)
        self.update_state(
            state="PROCESSING",
            meta={
                "progress": progress,
                "processed": processed,
                "total": total
            }
        )
    
    return {
        "status": "completed",
        "processed": processed
    }
```

### 任务链和工作流

```python
from celery import chain, group, chord

# 任务链：顺序执行
workflow = chain(
    fetch_data_task.s(url),
    process_data_task.s(),
    save_result_task.s()
)
result = workflow.apply_async()

# 任务组：并行执行
workflow = group(
    process_item_task.s(item)
    for item in items
)
result = workflow.apply_async()

# 和弦：并行执行后汇总
workflow = chord(
    group(
        process_item_task.s(item)
        for item in items
    ),
    aggregate_results_task.s()
)
result = workflow.apply_async()
```

### 任务优先级和队列

```python
# 定义不同优先级的队列
celery_app.conf.task_routes = {
    "tasks.email.*": {"queue": "email"},
    "tasks.data_processing.*": {"queue": "data_processing"},
    "tasks.maintenance.*": {"queue": "maintenance"},
}

# 高优先级任务
@celery_app.task(queue="high_priority")
def urgent_task():
    pass

# 发送到指定队列
send_email_task.apply_async(
    args=["user@example.com", "主题", "内容"],
    queue="email",
    priority=9  # 0-9, 9最高
)
```

---

## 定时任务

### 配置定时任务

```python
# app/core/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # 每天凌晨2点清理过期令牌
    "cleanup-expired-tokens": {
        "task": "app.tasks.maintenance.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),
    },
    
    # 每天凌晨3点清理旧审计日志
    "cleanup-old-audit-logs": {
        "task": "app.tasks.maintenance.cleanup_old_audit_logs",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"days": 90}
    },
    
    # 每小时清理临时文件
    "cleanup-temp-files": {
        "task": "app.tasks.maintenance.cleanup_temp_files",
        "schedule": crontab(minute=0),  # 每小时整点
    },
    
    # 每天早上8点发送日报
    "send-daily-report": {
        "task": "app.tasks.maintenance.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),
    },
    
    # 每5分钟健康检查
    "health-check": {
        "task": "app.tasks.maintenance.health_check",
        "schedule": 300,  # 每300秒
    },
    
    # 工作日每小时执行
    "business-hours-task": {
        "task": "app.tasks.business.process_orders",
        "schedule": crontab(
            hour="9-18",      # 9点到18点
            minute=0,
            day_of_week="1-5"  # 周一到周五
        ),
    },
}
```

### crontab 时间表达式

```python
from celery.schedules import crontab

# 每分钟
crontab()

# 每小时整点
crontab(minute=0)

# 每天凌晨
crontab(hour=0, minute=0)

# 每周一早上9点
crontab(hour=9, minute=0, day_of_week=1)

# 每月1号
crontab(hour=0, minute=0, day_of_month=1)

# 工作日每小时
crontab(minute=0, hour="9-18", day_of_week="1-5")

# 每15分钟
crontab(minute="*/15")

# 每天多个时间点
crontab(hour="8,12,18", minute=0)
```

---

## 任务监控

### 获取任务状态

```python
from celery.result import AsyncResult

# 获取任务结果
task_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
result = AsyncResult(task_id)

# 检查状态
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY

# 获取结果
if result.ready():
    print(result.result)

# 获取进度（自定义状态）
if result.state == "PROCESSING":
    print(result.info)  # {"progress": 50, "processed": 5, "total": 10}

# 等待结果
result = result.get(timeout=60)  # 等待60秒
```

### 在 API 中查询任务状态

```python
from fastapi import APIRouter
from celery.result import AsyncResult
from app.core.celery_app import celery_app

router = APIRouter()

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready()
    }
    
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    elif result.state == "PROCESSING":
        response["progress"] = result.info
    
    return response

@router.post("/tasks/{task_id}/revoke")
async def revoke_task(task_id: str):
    """取消任务"""
    celery_app.control.revoke(task_id, terminate=True)
    return {"message": "任务已取消", "task_id": task_id}
```

### Flower 监控面板

```bash
# 安装 Flower
pip install flower

# 启动监控面板
celery -A app.core.celery_app flower --port=5555

# 访问 http://localhost:5555
```

---

## 最佳实践

### 1. 幂等性设计

```python
@celery_app.task(bind=True)
def process_order_task(self, order_id: int):
    """处理订单（幂等设计）"""
    # 检查是否已处理
    order = get_order(order_id)
    if order.status == "processed":
        return {"status": "already_processed"}
    
    # 使用分布式锁防止重复处理
    lock_key = f"order_processing:{order_id}"
    if not acquire_lock(lock_key):
        return {"status": "processing_by_another"}
    
    try:
        process_order(order)
        return {"status": "processed"}
    finally:
        release_lock(lock_key)
```

### 2. 错误处理和重试

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,  # 指数退避
    retry_backoff_max=600,  # 最大重试间隔
    retry_jitter=True  # 随机抖动
)
def reliable_task(self, data):
    try:
        return process(data)
    except PermanentError:
        # 不重试的错误
        return {"status": "failed", "reason": "permanent_error"}
    except TransientError as exc:
        # 需要重试的错误
        raise self.retry(exc=exc, countdown=60)
```

### 3. 任务超时

```python
@celery_app.task(
    time_limit=300,      # 硬超时：5分钟
    soft_time_limit=240  # 软超时：4分钟（触发 SoftTimeLimitExceeded）
)
def time_limited_task(data):
    try:
        return long_process(data)
    except SoftTimeLimitExceeded:
        # 清理并优雅退出
        cleanup()
        return {"status": "timeout", "partial_result": get_partial_result()}
```

### 4. 大数据处理

```python
@celery_app.task
def process_large_dataset(dataset_id: int, batch_size: int = 100):
    """分批处理大数据集"""
    total = get_dataset_count(dataset_id)
    
    # 创建子任务批次
    tasks = []
    for offset in range(0, total, batch_size):
        task = process_batch_task.s(dataset_id, offset, batch_size)
        tasks.append(task)
    
    # 并行执行所有批次
    group(tasks).apply_async()
```

---

## 注意事项

1. **任务参数**: 任务参数必须可 JSON 序列化
2. **数据库连接**: 任务中需要独立创建数据库连接
3. **幂等设计**: 任务应设计为可重复执行
4. **超时设置**: 为长时间任务设置合理的超时
5. **错误处理**: 区分可重试和不可重试的错误
6. **资源清理**: 任务完成后清理临时资源
7. **监控告警**: 配置任务失败告警
8. **日志记录**: 记录任务执行日志便于排查问题
