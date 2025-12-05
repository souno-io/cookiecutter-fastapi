"""
Celery 异步任务配置。

提供后台任务处理功能，支持：
- 异步任务执行
- 定时任务调度
- 任务重试
- 任务监控
"""

from celery import Celery

from app.core.config import settings


# 创建 Celery 实例
celery_app = Celery(
    "worker",
    broker=getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务执行设置
    task_acks_late=True,  # 任务执行完成后再确认
    task_reject_on_worker_lost=True,  # Worker 丢失时拒绝任务
    
    # 任务结果设置
    result_expires=3600,  # 结果过期时间（秒）
    
    # 并发设置
    worker_concurrency=4,  # 并发 Worker 数量
    worker_prefetch_multiplier=1,  # 每个 Worker 预取任务数
    
    # 任务路由
    task_routes={
        "app.tasks.email.*": {"queue": "email"},
        "app.tasks.notification.*": {"queue": "notification"},
        "app.tasks.heavy.*": {"queue": "heavy"},
    },
    
    # 定时任务调度
    beat_schedule={
        # 示例：每小时执行清理任务
        "cleanup-expired-sessions": {
            "task": "app.tasks.maintenance.cleanup_expired_sessions",
            "schedule": 3600.0,  # 每小时
        },
        # 示例：每天凌晨2点执行统计任务
        "daily-stats": {
            "task": "app.tasks.maintenance.generate_daily_stats",
            "schedule": {
                "hour": 2,
                "minute": 0,
            },
        },
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks(["app.tasks"])
