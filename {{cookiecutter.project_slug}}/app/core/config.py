"""
应用配置管理，使用 Pydantic Settings。

支持多环境配置和 .env 文件加载。
"""

import json
from functools import lru_cache
from typing import Any, List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持环境变量。"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ===== 应用设置 =====
    APP_NAME: str = "{{ cookiecutter.project_name }}"
    APP_VERSION: str = "{{ cookiecutter.version }}"
    APP_DESCRIPTION: str = "{{ cookiecutter.project_description }}"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development, staging, production
    
    # ===== API 设置 =====
    API_V1_PREFIX: str = "/api/v1"
    OPENAPI_URL: Optional[str] = "/openapi.json"
    DOCS_URL: Optional[str] = "/docs"
    REDOC_URL: Optional[str] = "/redoc"
    
    # ===== 安全设置 =====
    SECRET_KEY: str = "{{ cookiecutter.jwt_secret_key }}"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ===== CORS 设置 =====
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def parse_list_field(cls, v: Union[str, List[str]]) -> List[str]:
        """解析列表字段，支持逗号分隔的字符串和 JSON 数组格式。"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # 尝试解析为 JSON 数组
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # 按逗号分隔
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
    
    # ===== 数据库设置 =====
    DATABASE_TYPE: str = "{{ cookiecutter.database_type }}"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "{{ cookiecutter.project_slug }}"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    @property
    def DATABASE_URL(self) -> str:
        """根据数据库类型构建数据库 URL。"""
        if self.DATABASE_TYPE == "postgresql":
            return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        elif self.DATABASE_TYPE == "mysql":
            return f"mysql+aiomysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        else:  # sqlite
            return f"sqlite+aiosqlite:///./{self.DATABASE_NAME}.db"
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """构建同步数据库 URL，用于 Alembic 迁移。"""
        if self.DATABASE_TYPE == "postgresql":
            return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        elif self.DATABASE_TYPE == "mysql":
            return f"mysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        else:  # sqlite
            return f"sqlite:///./{self.DATABASE_NAME}.db"
    
    {%- if cookiecutter.use_redis == "yes" %}
    # ===== Redis 设置 =====
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    @property
    def REDIS_URL(self) -> str:
        """构建 Redis URL。"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    {%- endif %}
    
    {%- if cookiecutter.use_celery == "yes" %}
    # ===== Celery 设置 =====
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    {%- endif %}
    
    # ===== 速率限制 =====
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # ===== 日志 =====
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # ===== 初始超级用户 =====
    FIRST_SUPERUSER_EMAIL: str = "{{ cookiecutter.first_superuser_email }}"
    FIRST_SUPERUSER_PASSWORD: str = "{{ cookiecutter.first_superuser_password }}"


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例。"""
    return Settings()


settings = get_settings()
