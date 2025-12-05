"""
自定义异常类定义。

提供统一的异常处理机制，支持：
- 业务异常
- 认证异常
- 权限异常
- 验证异常
- 资源不存在异常
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """
    应用基础异常类。
    
    所有自定义异常都应继承此类。
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化异常。
        
        参数：
            message: 错误消息
            error_code: 错误代码（用于前端识别）
            status_code: HTTP 状态码
            details: 额外的错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "APP_ERROR"
        self.status_code = status_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(AppException):
    """认证错误异常。"""
    
    def __init__(
        self,
        message: str = "认证失败",
        error_code: str = "AUTHENTICATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class AuthorizationError(AppException):
    """授权错误异常（权限不足）。"""
    
    def __init__(
        self,
        message: str = "权限不足",
        error_code: str = "AUTHORIZATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=403,
            details=details,
        )


class NotFoundError(AppException):
    """资源不存在异常。"""
    
    def __init__(
        self,
        message: str = "资源不存在",
        error_code: str = "NOT_FOUND",
        resource: Optional[str] = None,
        resource_id: Optional[Any] = None,
    ):
        details = {}
        if resource:
            details["resource"] = resource
        if resource_id:
            details["resource_id"] = str(resource_id)
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class ValidationError(AppException):
    """数据验证错误异常。"""
    
    def __init__(
        self,
        message: str = "数据验证失败",
        error_code: str = "VALIDATION_ERROR",
        errors: Optional[list] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=422,
            details={"errors": errors or []},
        )


class ConflictError(AppException):
    """资源冲突异常（如重复创建）。"""
    
    def __init__(
        self,
        message: str = "资源已存在",
        error_code: str = "CONFLICT",
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = str(value)
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=409,
            details=details,
        )


class RateLimitError(AppException):
    """速率限制异常。"""
    
    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=429,
            details=details,
        )


class BusinessError(AppException):
    """业务逻辑错误异常。"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "BUSINESS_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details,
        )


class ExternalServiceError(AppException):
    """外部服务错误异常。"""
    
    def __init__(
        self,
        message: str = "外部服务暂时不可用",
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        service_name: Optional[str] = None,
    ):
        details = {}
        if service_name:
            details["service"] = service_name
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=details,
        )


class DatabaseError(AppException):
    """数据库错误异常。"""
    
    def __init__(
        self,
        message: str = "数据库操作失败",
        error_code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details,
        )


class FileError(AppException):
    """文件操作错误异常。"""
    
    def __init__(
        self,
        message: str = "文件操作失败",
        error_code: str = "FILE_ERROR",
        filename: Optional[str] = None,
    ):
        details = {}
        if filename:
            details["filename"] = filename
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details,
        )
