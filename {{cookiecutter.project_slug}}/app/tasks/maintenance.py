"""
系统维护任务。

提供定时清理和统计功能。
"""

import logging
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.db.session import async_session_factory


logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_expired_sessions():
    """
    清理过期的会话/令牌。
    
    定时执行，清理数据库中过期的数据。
    """
    import asyncio
    
    async def _cleanup():
        async with async_session_factory() as session:
            # 示例：清理过期的令牌或会话
            # 根据实际需求修改
            logger.info("开始清理过期会话...")
            
            # 这里添加实际的清理逻辑
            # 例如：
            # from app.models import Session
            # from sqlalchemy import delete
            # stmt = delete(Session).where(Session.expires_at < datetime.utcnow())
            # result = await session.execute(stmt)
            # await session.commit()
            # logger.info(f"清理了 {result.rowcount} 条过期会话")
            
            logger.info("过期会话清理完成")
    
    asyncio.run(_cleanup())


@celery_app.task
def generate_daily_stats():
    """
    生成每日统计报告。
    
    每天定时执行，生成系统使用统计。
    """
    import asyncio
    
    async def _generate():
        async with async_session_factory() as session:
            logger.info("开始生成每日统计报告...")
            
            # 这里添加统计逻辑
            # 例如：统计用户数、请求数、活跃用户等
            stats = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "generated_at": datetime.now().isoformat(),
            }
            
            # 可以将统计数据保存到数据库或发送报告
            logger.info(f"每日统计报告: {stats}")
            
            logger.info("每日统计报告生成完成")
    
    asyncio.run(_generate())


@celery_app.task
def cleanup_old_files(days: int = 30):
    """
    清理旧文件。
    
    参数：
        days: 清理多少天前的文件
    """
    import os
    from pathlib import Path
    
    from app.core.config import settings
    
    upload_dir = Path(getattr(settings, 'UPLOAD_DIR', 'uploads'))
    if not upload_dir.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    for file_path in upload_dir.rglob("*"):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除文件失败: {file_path} - {e}")
    
    logger.info(f"清理了 {deleted_count} 个旧文件")


@celery_app.task
def health_check():
    """
    系统健康检查任务。
    
    检查各项服务是否正常。
    """
    import asyncio
    
    async def _check():
        results = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
        }
        
        # 检查数据库
        try:
            async with async_session_factory() as session:
                await session.execute("SELECT 1")
            results["services"]["database"] = "healthy"
        except Exception as e:
            results["services"]["database"] = f"unhealthy: {e}"
        
        # 检查 Redis
        try:
            from app.services.cache import cache_service
            await cache_service.set("health_check", "ok", 60)
            results["services"]["redis"] = "healthy"
        except Exception as e:
            results["services"]["redis"] = f"unhealthy: {e}"
        
        logger.info(f"健康检查结果: {results}")
        return results
    
    return asyncio.run(_check())
