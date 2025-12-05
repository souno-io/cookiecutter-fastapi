"""
全局异常处理器。

提供统一的异常处理和响应格式。
"""

import logging
import traceback
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException
from app.core.config import settings


logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    设置全局异常处理器。
    
    参数：
        app: FastAPI 应用实例
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, 
        exc: AppException,
    ) -> JSONResponse:
        """处理应用自定义异常。"""
        logger.warning(
            f"应用异常 | "
            f"路径: {request.url.path} | "
            f"错误码: {exc.error_code} | "
            f"消息: {exc.message}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """处理请求验证错误。"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        logger.warning(
            f"验证错误 | "
            f"路径: {request.url.path} | "
            f"错误数: {len(errors)}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "请求数据验证失败",
                "details": {"errors": errors},
            },
        )
    
    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_exception_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """处理 Pydantic 验证错误。"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "数据验证失败",
                "details": {"errors": errors},
            },
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        """处理数据库错误。"""
        logger.error(
            f"数据库错误 | "
            f"路径: {request.url.path} | "
            f"错误: {str(exc)}"
        )
        
        # 生产环境不暴露详细错误
        message = "数据库操作失败"
        details = {}
        
        if settings.DEBUG:
            details["error"] = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "error_code": "DATABASE_ERROR",
                "message": message,
                "details": details,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """处理未捕获的异常。"""
        # 记录完整的堆栈跟踪
        logger.error(
            f"未处理异常 | "
            f"路径: {request.url.path} | "
            f"类型: {type(exc).__name__} | "
            f"消息: {str(exc)}\n"
            f"堆栈: {traceback.format_exc()}"
        )
        
        # 生产环境不暴露详细错误
        message = "服务器内部错误"
        details = {}
        
        if settings.DEBUG:
            details["error"] = str(exc)
            details["type"] = type(exc).__name__
            details["traceback"] = traceback.format_exc().split("\n")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "error_code": "INTERNAL_ERROR",
                "message": message,
                "details": details,
            },
        )


class ErrorResponse:
    """
    错误响应工具类。
    
    用于在 OpenAPI 文档中定义错误响应模式。
    """
    
    @staticmethod
    def responses(
        *status_codes: int,
    ) -> dict:
        """
        生成 OpenAPI 错误响应定义。
        
        用法：
            @router.get(
                "/items/{id}",
                responses=ErrorResponse.responses(404, 403),
            )
        """
        response_map = {
            400: {
                "description": "请求错误",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "BAD_REQUEST",
                            "message": "请求参数错误",
                            "details": {},
                        }
                    }
                },
            },
            401: {
                "description": "未认证",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "AUTHENTICATION_ERROR",
                            "message": "认证失败",
                            "details": {},
                        }
                    }
                },
            },
            403: {
                "description": "权限不足",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "AUTHORIZATION_ERROR",
                            "message": "权限不足",
                            "details": {},
                        }
                    }
                },
            },
            404: {
                "description": "资源不存在",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "NOT_FOUND",
                            "message": "资源不存在",
                            "details": {"resource": "item", "resource_id": "123"},
                        }
                    }
                },
            },
            409: {
                "description": "资源冲突",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "CONFLICT",
                            "message": "资源已存在",
                            "details": {"field": "email"},
                        }
                    }
                },
            },
            422: {
                "description": "验证错误",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "VALIDATION_ERROR",
                            "message": "数据验证失败",
                            "details": {
                                "errors": [
                                    {"field": "email", "message": "无效的邮箱格式"}
                                ]
                            },
                        }
                    }
                },
            },
            429: {
                "description": "请求过于频繁",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "RATE_LIMIT_EXCEEDED",
                            "message": "请求过于频繁，请稍后再试",
                            "details": {"retry_after": 60},
                        }
                    }
                },
            },
            500: {
                "description": "服务器错误",
                "content": {
                    "application/json": {
                        "example": {
                            "error": True,
                            "error_code": "INTERNAL_ERROR",
                            "message": "服务器内部错误",
                            "details": {},
                        }
                    }
                },
            },
        }
        
        return {code: response_map[code] for code in status_codes if code in response_map}
