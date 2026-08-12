"""海外管理绩效汇报 Schema。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CriterionConfig(BaseModel):
    code: Literal["c1", "c2", "c3", "c4", "c5", "c6", "c7"]
    title: str
    required: bool = False
    requirement: str
    evidence_requirements: list[str]
    enabled: bool = True
    thresholds: dict[str, Union[float, int]]


class PerformanceConfigView(BaseModel):
    enabled: bool
    scope: Literal["all_projects", "owned_projects"]
    schedule_frequency: Literal["monthly", "quarterly"]
    schedule_day: int = Field(..., ge=1, le=28)
    schedule_hour: int = Field(..., ge=0, le=23)
    schedule_minute: int = Field(..., ge=0, le=59)
    criteria: list[CriterionConfig]
    last_run_at: Optional[datetime] = None


class PerformanceConfigUpdate(PerformanceConfigView):
    last_run_at: Optional[datetime] = Field(None, exclude=True)


class GeneratePerformanceReportRequest(BaseModel):
    period_type: Literal[
        "current_month", "previous_month", "current_quarter", "previous_quarter", "custom"
    ] = "current_quarter"
    start_date: date
    end_date: date
    period_label: str = Field(..., min_length=2, max_length=100)
    scope: Optional[Literal["all_projects", "owned_projects"]] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("结束日期不能早于开始日期")
        if (self.end_date - self.start_date).days > 370:
            raise ValueError("单次汇总时间范围不能超过 370 天")
        return self


class PerformanceReportListItem(BaseModel):
    id: UUID
    period_label: str
    period_type: str
    start_date: date
    end_date: date
    scope: str
    trigger_type: str
    status: str
    generated_at: datetime


class PerformanceReportDetail(PerformanceReportListItem):
    summary: dict[str, Any]
    error_message: Optional[str] = None


class PerformanceReportList(BaseModel):
    items: list[PerformanceReportListItem]
    total: int
