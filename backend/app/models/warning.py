"""
预警模型

预警规则引擎相关数据模型。
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4, UUID

from sqlalchemy import String, DateTime, Date, Text, Boolean, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import WarningSeverity, WarningStatus


class WarningRule(Base):
    """预警规则表模型"""
    
    __tablename__ = "warning_rules"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 规则条件（JSON 格式存储）
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # 规则配置
    severity: Mapped[WarningSeverity] = mapped_column(nullable=False)
    notify_targets: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # ["project_owner", "pmo"]
    notify_channels: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # ["dingtalk", "system"]
    cooldown_days: Mapped[int] = mapped_column(default=7, nullable=False)
    
    # 规则状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # 关系
    instances = relationship("WarningInstance", back_populates="rule", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<WarningRule {self.rule_code}: {self.rule_name}>"


class WarningInstance(Base):
    """预警实例表模型"""
    
    __tablename__ = "warning_instances"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # 关联字段
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("warning_rules.id"), nullable=False, index=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    channel_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    
    # 预警内容
    severity: Mapped[WarningSeverity] = mapped_column(nullable=False, index=True)
    status: Mapped[WarningStatus] = mapped_column(nullable=False, default=WarningStatus.ACTIVE, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 处理信息
    handled_by: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    handle_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 通知状态
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # 关系
    rule = relationship("WarningRule", back_populates="instances")
    project = relationship("Project", back_populates="warnings")
    
    def __repr__(self) -> str:
        return f"<WarningInstance {self.severity}: {self.message[:50]}>"
