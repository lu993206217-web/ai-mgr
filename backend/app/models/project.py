"""
项目模型

项目主档案（Project Master），系统的核心业务实体。
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import String, DateTime, Date, Enum as SQLEnum, Boolean, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import ProjectStage, ProjectStatus, HealthStatus, RiskLevel, ProjectSourceType


class Project(Base):
    """项目表模型"""
    
    __tablename__ = "projects"
    
    # 主键
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # 核心字段
    project_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    channel_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # 金额字段
    project_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    
    # 项目来源和阶段
    source_type: Mapped[ProjectSourceType] = mapped_column(nullable=False)
    current_stage: Mapped[ProjectStage] = mapped_column(nullable=False, default=ProjectStage.PRE_SALE)
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 计划时间
    planned_go_live: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_acceptance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # 状态字段
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    health_status: Mapped[HealthStatus] = mapped_column(nullable=False, default=HealthStatus.HEALTHY, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(nullable=False, default=RiskLevel.LOW, index=True)
    status: Mapped[ProjectStatus] = mapped_column(nullable=False, default=ProjectStatus.IN_PROGRESS, index=True)
    
    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # 关系
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    customer = relationship("Customer", back_populates="projects")
    channel = relationship("Channel", back_populates="projects")
    activities = relationship("ActivityLog", back_populates="project", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="project", cascade="all, delete-orphan")
    warnings = relationship("WarningInstance", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Project {self.project_name}>"
    
    @property
    def health_status_computed(self) -> HealthStatus:
        """根据最后活动时间和阻塞状态计算健康度"""
        # 新建项目（创建时间在7天内）且没有活动时，默认健康状态为健康
        if not self.last_activity_at:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            days_since_created = (now - self.created_at).days
            if days_since_created <= 7:
                return HealthStatus.HEALTHY
            return HealthStatus.SERIOUS_RISK
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        days_since_activity = (now - self.last_activity_at).days
        
        # 检查是否有阻塞活动（处理可能的异常）
        has_blocker = False
        try:
            if self.activities:
                has_blocker = any(activity.blocker_flag for activity in self.activities)
        except Exception:
            has_blocker = False
        
        if days_since_activity <= 7:
            # 如果有阻塞，即使活动频繁也降级为关注状态
            return HealthStatus.ATTENTION if has_blocker else HealthStatus.HEALTHY
        elif days_since_activity <= 14:
            # 如果有阻塞，降级为风险状态
            return HealthStatus.RISK if has_blocker else HealthStatus.ATTENTION
        elif days_since_activity <= 30:
            # 如果有阻塞，降级为严重风险状态
            return HealthStatus.SERIOUS_RISK if has_blocker else HealthStatus.RISK
        else:
            return HealthStatus.SERIOUS_RISK
