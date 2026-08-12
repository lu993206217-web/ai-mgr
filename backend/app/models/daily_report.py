"""
项目活动日报同步模型

保存外部日报项目与本系统项目的绑定、未匹配队列、导入去重记录和同步运行记录。
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import String, DateTime, Date, Text, Boolean, Numeric, JSON, ForeignKey, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class DailyReportBinding(Base):
    """外部日报项目与本系统项目绑定"""

    __tablename__ = "daily_report_bindings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    external_project_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    match_method: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    match_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    last_sync_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    project = relationship("Project")


class DailyReportProjectAlias(Base):
    """本地项目对应的日报简称、历史名称和不同 project_key 入口。"""

    __tablename__ = "daily_report_project_aliases"
    __table_args__ = (
        UniqueConstraint("project_id", "normalized_alias", name="uq_daily_project_alias"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_project_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_method: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project")


class DailyReportUnmatchedProject(Base):
    """未自动匹配的外部日报项目"""

    __tablename__ = "daily_report_unmatched_projects"
    __table_args__ = (
        UniqueConstraint("month", "project_key", name="uq_daily_unmatched_month_project_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    month: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_project_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    active_days: Mapped[int] = mapped_column(default=0, nullable=False)
    last_active_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pre_sales_entry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    implementation_entry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    service_entry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    suggested_project_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    suggested_project_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    suggested_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="待处理", index=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    handled_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    suggested_project = relationship("Project")


class DailyReportActivityMapping(Base):
    """外部日报条目到活动日志的映射，用于幂等去重"""

    __tablename__ = "daily_report_activity_mappings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    activity_log_id: Mapped[UUID] = mapped_column(ForeignKey("activity_logs.id"), nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    employee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fact_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project")
    activity = relationship("ActivityLog")


class DailyReportSyncRun(Base):
    """日报同步运行记录"""

    __tablename__ = "daily_report_sync_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="运行中", index=True)
    lookback_days: Mapped[int] = mapped_column(default=3, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    options_count: Mapped[int] = mapped_column(default=0, nullable=False)
    auto_bound_count: Mapped[int] = mapped_column(default=0, nullable=False)
    unmatched_count: Mapped[int] = mapped_column(default=0, nullable=False)
    imported_activity_count: Mapped[int] = mapped_column(default=0, nullable=False)
    skipped_duplicate_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)


class DailyReportRawEntry(Base):
    """外部日报原始条目。

    先于项目匹配和活动导入落库，原始载荷不被 AI 分析结果覆盖。
    """

    __tablename__ = "daily_report_raw_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sync_run_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("daily_report_sync_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="rd-dynamics")
    source_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    project_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_project_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    creator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    original_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    analysis_status: Mapped[str] = mapped_column(String(20), nullable=False, default="待分析", index=True)
    ai_project_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_activity_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    ai_occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activity_log_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("activity_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project")
    activity = relationship("ActivityLog")
