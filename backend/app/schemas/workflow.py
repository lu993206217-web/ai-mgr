"""流程中心 API Schema。"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowEvidenceView(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    activity_id: Optional[UUID] = None
    evidence_at: datetime
    summary: str
    decision: str
    confidence: Optional[float] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class WorkflowStateEventView(BaseModel):
    id: UUID
    from_status: Optional[str] = None
    to_status: str
    source: str
    reason: Optional[str] = None
    confidence: Optional[float] = None
    changed_by: Optional[UUID] = None
    occurred_at: datetime

    class Config:
        from_attributes = True


class WorkflowItemView(BaseModel):
    id: UUID
    project_id: UUID
    project_name: Optional[str] = None
    owner_id: Optional[UUID] = None
    owner_name: Optional[str] = None
    title: str
    description: str
    status: str
    responsibility_party: str
    priority: str
    due_date: Optional[date] = None
    source_type: str
    ai_generated: bool
    ai_confidence: Optional[float] = None
    ai_reason: Optional[str] = None
    last_progress_at: datetime
    completed_at: Optional[datetime] = None
    evidence_count: int = 0
    alert_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowItemDetail(WorkflowItemView):
    evidences: list[WorkflowEvidenceView] = Field(default_factory=list)
    state_events: list[WorkflowStateEventView] = Field(default_factory=list)


class WorkflowTransitionRequest(BaseModel):
    status: str = Field(..., min_length=2, max_length=30)
    note: Optional[str] = Field(None, max_length=1000)


class WorkflowItemCreate(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=2, max_length=300)
    description: str = Field("", max_length=4000)
    owner_id: Optional[UUID] = None
    responsibility_party: str = Field("我方", max_length=30)
    priority: str = Field("普通", max_length=20)
    due_date: Optional[date] = None


class WorkflowAssignRequest(BaseModel):
    owner_id: UUID


class WorkflowSummary(BaseModel):
    total_open: int
    ai_pending: int
    mine_pending: int
    waiting_external: int
    due_today: int
    overdue: int
    suspected_complete: int
    active_alerts: int


class WorkflowAlertView(BaseModel):
    id: UUID
    workflow_item_id: Optional[UUID] = None
    project_id: UUID
    project_name: Optional[str] = None
    item_title: Optional[str] = None
    alert_type: str
    level: str
    status: str
    threshold_days: int
    elapsed_days: int
    message: str
    evidence_at: Optional[datetime] = None
    first_triggered_at: datetime
    last_evaluated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowAlertHandleRequest(BaseModel):
    status: str = Field(..., pattern="^(已解除|已忽略)$")
    note: Optional[str] = Field(None, max_length=1000)


class WorkflowAutomationTaskView(BaseModel):
    id: UUID
    task_code: str
    task_name: str
    description: str
    enabled: bool
    schedule_type: str
    interval_minutes: Optional[int] = None
    schedule_hour: Optional[int] = None
    schedule_minute: Optional[int] = None
    lookback_days: Optional[int] = None
    source_ready: bool = True
    source_message: Optional[str] = None
    next_run_at: Optional[datetime] = None
    last_started_at: Optional[datetime] = None
    last_finished_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_result: Optional[str] = None
    last_error: Optional[str] = None

    class Config:
        from_attributes = True


class WorkflowAutomationTaskUpdate(BaseModel):
    enabled: bool
    schedule_type: str = Field(..., pattern="^(interval|daily)$")
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    schedule_hour: Optional[int] = Field(None, ge=0, le=23)
    schedule_minute: Optional[int] = Field(None, ge=0, le=59)
    lookback_days: Optional[int] = Field(None, ge=1, le=31)


class WorkflowAutomationRunView(BaseModel):
    id: UUID
    task_id: UUID
    task_name: Optional[str] = None
    trigger_type: str
    status: str
    result_json: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
