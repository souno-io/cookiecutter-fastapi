"""
审计日志服务模块。

提供操作日志记录功能。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


logger = logging.getLogger(__name__)


class AuditAction:
    """审计操作类型常量。"""
    
    # 用户操作
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_PASSWORD_CHANGE = "user.password_change"
    USER_PASSWORD_RESET = "user.password_reset"
    
    # 角色操作
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    ROLE_ASSIGN = "role.assign"
    
    # 权限操作
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_REVOKE = "permission.revoke"
    
    # 资源操作
    RESOURCE_CREATE = "resource.create"
    RESOURCE_UPDATE = "resource.update"
    RESOURCE_DELETE = "resource.delete"
    RESOURCE_VIEW = "resource.view"
    
    # 文件操作
    FILE_UPLOAD = "file.upload"
    FILE_DELETE = "file.delete"
    FILE_DOWNLOAD = "file.download"
    
    # 系统操作
    SYSTEM_CONFIG_UPDATE = "system.config_update"
    SYSTEM_MAINTENANCE = "system.maintenance"


class AuditLogService:
    """
    审计日志服务类。
    
    提供日志记录和查询功能。
    """
    
    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str = None,
        description: str = None,
        old_value: Dict[str, Any] = None,
        new_value: Dict[str, Any] = None,
        user: User = None,
        request: Request = None,
        status: str = "success",
        error_message: str = None,
    ) -> AuditLog:
        """
        记录审计日志。
        
        参数：
            db: 数据库会话
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源 ID
            description: 操作描述
            old_value: 旧值（用于记录变更）
            new_value: 新值（用于记录变更）
            user: 操作用户
            request: HTTP 请求对象
            status: 操作状态（success/failure）
            error_message: 错误信息
            
        返回：
            创建的审计日志对象
        """
        # 提取请求信息
        ip_address = None
        user_agent = None
        request_id = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")[:500]
            request_id = getattr(request.state, "request_id", None)
        
        # 创建日志记录
        audit_log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            description=description,
            old_value=old_value,
            new_value=new_value,
            user_id=user.id if user else None,
            username=user.username if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
        )
        
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        
        logger.info(
            f"审计日志 | {action} | {resource_type}:{resource_id} | "
            f"用户: {user.username if user else 'anonymous'} | "
            f"状态: {status}"
        )
        
        return audit_log
    
    @staticmethod
    async def log_success(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str = None,
        description: str = None,
        user: User = None,
        request: Request = None,
        **kwargs,
    ) -> AuditLog:
        """记录成功操作日志。"""
        return await AuditLogService.log(
            db=db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            user=user,
            request=request,
            status="success",
            **kwargs,
        )
    
    @staticmethod
    async def log_failure(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: str = None,
        description: str = None,
        error_message: str = None,
        user: User = None,
        request: Request = None,
        **kwargs,
    ) -> AuditLog:
        """记录失败操作日志。"""
        return await AuditLogService.log(
            db=db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            user=user,
            request=request,
            status="failure",
            error_message=error_message,
            **kwargs,
        )
    
    @staticmethod
    async def get_logs(
        db: AsyncSession,
        user_id: int = None,
        action: str = None,
        resource_type: str = None,
        resource_id: str = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AuditLog]:
        """
        查询审计日志。
        
        参数：
            db: 数据库会话
            user_id: 用户 ID 过滤
            action: 操作类型过滤
            resource_type: 资源类型过滤
            resource_id: 资源 ID 过滤
            status: 状态过滤
            start_date: 开始时间
            end_date: 结束时间
            skip: 跳过数量
            limit: 返回数量
            
        返回：
            审计日志列表
        """
        query = select(AuditLog)
        
        # 应用过滤条件
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if status:
            query = query.where(AuditLog.status == status)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        # 排序和分页
        query = query.order_by(desc(AuditLog.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_user_activity(
        db: AsyncSession,
        user_id: int,
        days: int = 30,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        获取用户活动记录。
        
        参数：
            db: 数据库会话
            user_id: 用户 ID
            days: 最近天数
            limit: 返回数量
        """
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        return await AuditLogService.get_logs(
            db=db,
            user_id=user_id,
            start_date=start_date,
            limit=limit,
        )
    
    @staticmethod
    async def get_resource_history(
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
    ) -> List[AuditLog]:
        """
        获取资源操作历史。
        
        参数：
            db: 数据库会话
            resource_type: 资源类型
            resource_id: 资源 ID
            limit: 返回数量
        """
        return await AuditLogService.get_logs(
            db=db,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
        )


# 审计日志装饰器
def audit_log(
    action: str,
    resource_type: str,
    get_resource_id: callable = None,
    description: str = None,
):
    """
    审计日志装饰器。
    
    用法：
        @audit_log(
            action=AuditAction.USER_UPDATE,
            resource_type="user",
            get_resource_id=lambda args: args[1],  # 从参数获取资源ID
        )
        async def update_user(db, user_id, data):
            ...
    
    参数：
        action: 操作类型
        resource_type: 资源类型
        get_resource_id: 获取资源 ID 的函数
        description: 操作描述
    """
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 尝试从参数获取 db 和 user
            db = kwargs.get("db") or (args[0] if args else None)
            user = kwargs.get("current_user")
            request = kwargs.get("request")
            
            # 获取资源 ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(args, kwargs)
                except:
                    pass
            
            try:
                result = await func(*args, **kwargs)
                
                # 记录成功日志
                if db and hasattr(db, 'add'):
                    await AuditLogService.log_success(
                        db=db,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        description=description,
                        user=user,
                        request=request,
                    )
                
                return result
                
            except Exception as e:
                # 记录失败日志
                if db and hasattr(db, 'add'):
                    await AuditLogService.log_failure(
                        db=db,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        description=description,
                        error_message=str(e),
                        user=user,
                        request=request,
                    )
                raise
        
        return wrapper
    return decorator


# 全局服务实例
audit_service = AuditLogService()
