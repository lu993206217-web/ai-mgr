"""项目状态历史与每日情报快照。"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ProjectStateEvent(Base):
    """项目阶段、状态变化的不可覆盖历史记录。"""

    __tablename__ = "project_state_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    from_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    to_value: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    changed_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project = relationship("Project", back_populates="state_events")


class ProjectIntelligenceSnapshot(Base):
    """每天一条项目情报快照，用于可信趋势而不是前端写死百分比。"""

    __tablename__ = "project_intelligence_snapshots"
    __table_args__ = (
        UniqueConstraint("project_id", "snapshot_date", name="uq_project_snapshot_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    project_status: Mapped[str] = mapped_column(String(30), nullable=False)
    project_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    health_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    inactivity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activity_count_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activity_count_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overdue_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_counts_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project = relationship("Project", back_populates="intelligence_snapshots")
