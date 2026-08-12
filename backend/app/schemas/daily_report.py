"""
项目活动日报同步 Schema。
"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DailyReportSyncRequest(BaseModel):
    month: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    project_ids: Optional[list[UUID]] = None
    lookback_days: Optional[int] = Field(None, ge=1, le=31)
    trigger_ingestion: bool = False


class DailyReportSyncRun(BaseModel):
    id: UUID
    month: str
    trigger_type: str
    status: str
    lookback_days: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    options_count: int
    auto_bound_count: int
    unmatched_count: int
    imported_activity_count: int
    skipped_duplicate_count: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DailyReportBinding(BaseModel):
    id: UUID
    project_id: UUID
    project_key: str
    external_project_name: str
    match_method: str
    match_score: float
    is_active: bool
    last_sync_month: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None

    class Config:
        from_attributes = True


class DailyReportUnmatchedProject(BaseModel):
    id: UUID
    month: str
    project_key: str
    external_project_name: str
    active_days: int
    last_active_date: Optional[date] = None
    pre_sales_entry_count: int
    implementation_entry_count: int
    service_entry_count: int
    suggested_project_id: Optional[UUID] = None
    suggested_project_name: Optional[str] = None
    suggested_score: float
    status: str
    created_at: datetime
    updated_at: datetime
    handled_at: Optional[datetime] = None
    imported_activity_count: int = 0
    skipped_duplicate_count: int = 0
    sample_original_summary: Optional[str] = None
    sample_ai_reason: Optional[str] = None
    sample_creator_name: Optional[str] = None
    sample_source_date: Optional[date] = None
    source_project_names: list[str] = Field(default_factory=list)
    diagnosis_hint: Optional[str] = None

    class Config:
        from_attributes = True


class BindUnmatchedRequest(BaseModel):
    project_id: UUID
    sync_after_bind: bool = True


class DailyReportRawEntry(BaseModel):
    id: UUID
    sync_run_id: Optional[UUID] = None
    source_date: date
    project_key: str
    external_project_name: str
    creator_name: Optional[str] = None
    original_summary: str
    source_occurred_at: Optional[datetime] = None
    analysis_status: str
    ai_project_id: Optional[UUID] = None
    ai_project_name: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_reason: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_activity_type: Optional[str] = None
    ai_occurred_at: Optional[datetime] = None
    error_message: Optional[str] = None
    activity_log_id: Optional[UUID] = None
    analyzed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
