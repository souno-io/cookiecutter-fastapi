"""
审计日志模型。

记录系统操作历史。
"""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """
    审计日志模型。
    
    记录用户的操作历史，用于安全审计和问题追踪。
    """
    
    __tablename__ = "audit_logs"
    
    # 操作信息
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="操作类型")
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="资源类型")
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="资源ID")
    
    # 操作详情
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="操作描述")
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="旧值")
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="新值")
    
    # 操作者信息
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="操作用户ID")
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="操作用户名")
    
    # 请求信息
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="用户代理")
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="请求ID")
    
    # 结果信息
    status: Mapped[str] = mapped_column(String(20), default="success", comment="操作状态")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    
    # 关联
    user = relationship("User", backref="audit_logs")
    
    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}:{self.resource_id}>"
