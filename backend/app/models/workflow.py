"""流程中心模型。

流程事项与原始邮件、日报、活动日志分层保存。事项状态可以由新证据推进，
但每次变化都会追加历史，不覆盖原始事实。
"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class WorkflowItem(Base):
    """需要持续推进和闭环的业务事项。"""

    __tablename__ = "workflow_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="待接收", index=True)
    responsibility_party: Mapped[str] = mapped_column(
        String(30), nullable=False, default="我方", index=True
    )
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="普通", index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[Optional[UUID]] = mapped_column(nullable=True, index=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_progress_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project")
    owner = relationship("User")
    evidences = relationship(
        "WorkflowEvidence", back_populates="workflow_item", cascade="all, delete-orphan"
    )
    state_events = relationship(
        "WorkflowStateEvent", back_populates="workflow_item", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "WorkflowAlert", back_populates="workflow_item", cascade="all, delete-orphan"
    )


class WorkflowEvidence(Base):
    """事项的推进证据，可追溯到邮件、日报或活动日志。"""

    __tablename__ = "workflow_evidences"
    __table_args__ = (
        UniqueConstraint(
            "workflow_item_id", "source_type", "source_id", name="uq_workflow_evidence_source"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    activity_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("activity_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, default="记录进展")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow_item = relationship("WorkflowItem", back_populates="evidences")
    activity = relationship("ActivityLog")


class WorkflowStateEvent(Base):
    """事项状态变化历史。"""

    __tablename__ = "workflow_state_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="system")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("workflow_evidences.id", ondelete="SET NULL"), nullable=True
    )
    changed_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    workflow_item = relationship("WorkflowItem", back_populates="state_events")


class WorkflowAlert(Base):
    """支持自动升级和自动解除的流程告警。"""

    __tablename__ = "workflow_alerts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    condition_key: Mapped[str] = mapped_column(String(300), nullable=False, unique=True, index=True)
    workflow_item_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("workflow_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="提醒", index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="活跃", index=True)
    threshold_days: Mapped[int] = mapped_column(nullable=False, default=0)
    elapsed_days: Mapped[int] = mapped_column(nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    handled_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    handle_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workflow_item = relationship("WorkflowItem", back_populates="alerts")
    project = relationship("Project")


class WorkflowAutomationTask(Base):
    """可在页面管理的无人值守推进任务。"""

    __tablename__ = "workflow_automation_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False, default="interval")
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lookback_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    runs = relationship(
        "WorkflowAutomationRun", back_populates="task", cascade="all, delete-orphan"
    )


class WorkflowAutomationRun(Base):
    """自动推进任务的每次运行记录。"""

    __tablename__ = "workflow_automation_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_automation_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="排队中", index=True)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    task = relationship("WorkflowAutomationTask", back_populates="runs")
