"""服务模块导出。"""

from app.services.base import BaseService
from app.services.user import UserService
from app.services.auth import AuthService
from app.services.email import EmailService, email_service, EmailTemplates
from app.services.file import FileService, file_service
from app.services.cache import CacheService, cache_service, cached
from app.services.audit import AuditLogService, audit_service, AuditAction

__all__ = [
    # 基础服务
    "BaseService",
    "UserService",
    "AuthService",
    # 邮件服务
    "EmailService",
    "email_service",
    "EmailTemplates",
    # 文件服务
    "FileService",
    "file_service",
    # 缓存服务
    "CacheService",
    "cache_service",
    "cached",
    # 审计服务
    "AuditLogService",
    "audit_service",
    "AuditAction",
]
