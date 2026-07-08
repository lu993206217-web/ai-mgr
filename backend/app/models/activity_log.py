"""
Activity Log 模型

唯一业务事实源，记录所有项目活动。
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import String, DateTime, Date, Text, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import ActivityType, NextAction, ActivitySource


class ActivityLog(Base):
    """Activity Log 表模型"""
    
    __tablename__ = "activity_logs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # 关联字段（可为空，支持未匹配状态）
    project_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    channel_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)
    
    # 活动核心字段
    activity_type: Mapped[ActivityType] = mapped_column(nullable=False)
    activity_content: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[Optional[NextAction]] = mapped_column(nullable=True)
    next_action_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    blocker_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 负责人
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # 来源
    source: Mapped[ActivitySource] = mapped_column(nullable=False)
    source_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    
    # 时间字段（occurred_at 与 created_at 分离）
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 关系
    project = relationship("Project", back_populates="activities")
    channel = relationship("Channel")
    owner = relationship("User", back_populates="activities")
    
    def __repr__(self) -> str:
        return f"<ActivityLog {self.activity_type}: {self.activity_content[:50]}>"
