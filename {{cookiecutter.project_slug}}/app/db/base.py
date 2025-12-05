"""
SQLAlchemy 基础模型，包含通用字段和方法。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    所有 SQLAlchemy 模型的基类。
    
    提供：
    - 自动表命名
    - 通用时间戳字段
    - 主键 id 字段
    """
    
    id: Any
    __name__: str
    
    # 从类名自动生成 __tablename__
    @declared_attr
    def __tablename__(cls) -> str:
        """从类名生成表名（snake_case）。"""
        import re
        name = cls.__name__
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    
    # 通用字段
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    def to_dict(self) -> dict:
        """将模型实例转换为字典。"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs) -> None:
        """更新模型属性。"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
