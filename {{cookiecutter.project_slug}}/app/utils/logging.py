"""
日志配置增强模块。

提供结构化日志和上下文日志功能。
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


# 请求上下文变量
request_context: ContextVar[Dict[str, Any]] = ContextVar(
    "request_context",
    default={},
)


class LogRecord(BaseModel):
    """结构化日志记录模型。"""
    
    timestamp: str
    level: str
    logger: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    extra: Dict[str, Any] = {}


class JsonFormatter(logging.Formatter):
    """JSON 格式化器。"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON。"""
        # 基本信息
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加请求上下文
        ctx = request_context.get()
        if ctx:
            log_data["request_id"] = ctx.get("request_id")
            log_data["user_id"] = ctx.get("user_id")
        
        # 添加额外字段
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ContextLogger:
    """
    上下文日志器。
    
    自动附加请求上下文信息到日志。
    """
    
    def __init__(self, name: str):
        """初始化日志器。"""
        self._logger = logging.getLogger(name)
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """内部日志方法。"""
        extra = kwargs.pop("extra", {})
        
        # 合并上下文
        ctx = request_context.get()
        extra.update(ctx)
        
        self._logger.log(level, msg, *args, extra={"extra": extra}, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        """调试日志。"""
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """信息日志。"""
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """警告日志。"""
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """错误日志。"""
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """严重错误日志。"""
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """异常日志（自动包含堆栈）。"""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)


def get_logger(name: str) -> ContextLogger:
    """
    获取上下文日志器。
    
    用法：
        logger = get_logger(__name__)
        logger.info("用户登录", extra={"user_id": 123})
    """
    return ContextLogger(name)


def set_request_context(
    request_id: str = None,
    user_id: int = None,
    **kwargs,
) -> None:
    """
    设置请求上下文。
    
    参数：
        request_id: 请求 ID
        user_id: 用户 ID
        **kwargs: 其他上下文数据
    """
    ctx = request_context.get().copy()
    
    if request_id:
        ctx["request_id"] = request_id
    if user_id:
        ctx["user_id"] = user_id
    ctx.update(kwargs)
    
    request_context.set(ctx)


def clear_request_context() -> None:
    """清除请求上下文。"""
    request_context.set({})


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: str = None,
) -> None:
    """
    配置日志系统。
    
    参数：
        level: 日志级别
        json_format: 是否使用 JSON 格式
        log_file: 日志文件路径
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 创建格式化器
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class LogContextMiddleware:
    """
    日志上下文中间件。
    
    自动设置和清理请求上下文。
    """
    
    def __init__(self, app):
        """初始化中间件。"""
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """处理请求。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # 从 scope 获取请求 ID（由 RequestIDMiddleware 设置）
        request_id = scope.get("state", {}).get("request_id")
        
        if request_id:
            set_request_context(request_id=request_id)
        
        try:
            await self.app(scope, receive, send)
        finally:
            clear_request_context()
