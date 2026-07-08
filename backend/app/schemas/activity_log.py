"""
Activity Log Schema

活动日志的 Pydantic 模型。
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ============ 基础 Schema ============
class ActivityLogBase(BaseModel):
    """Activity Log 基础 Schema"""
    project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    
    activity_type: str = Field(..., description="活动类型")
    activity_content: str = Field(..., min_length=1, max_length=2000)
    next_action: Optional[str] = Field(None, description="下一步动作")
    next_action_deadline: Optional[date] = None
    blocker_flag: bool = Field(default=False)
    
    owner_id: UUID
    source: str = Field(default="手工录入", description="活动来源")
    source_id: Optional[UUID] = None
    
    occurred_at: datetime


class ActivityLogCreate(ActivityLogBase):
    """Activity Log 创建 Schema"""
    pass


class ActivityLogUpdate(BaseModel):
    """Activity Log 更新 Schema"""
    activity_type: Optional[str] = None
    activity_content: Optional[str] = Field(None, min_length=1, max_length=2000)
    next_action: Optional[str] = None
    next_action_deadline: Optional[date] = None
    blocker_flag: Optional[bool] = None


class ActivityLogInDB(ActivityLogBase):
    """Activity Log 数据库 Schema"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ActivityLog(ActivityLogInDB):
    """Activity Log 响应 Schema"""
    project_name: Optional[str] = None
    channel_name: Optional[str] = None
    owner_name: Optional[str] = None


# ============ 查询参数 Schema ============
class ActivityLogQueryParams(BaseModel):
    """Activity Log 查询参数 Schema"""
    project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    
    activity_type: Optional[str] = None
    next_action: Optional[str] = None
    blocker_flag: Optional[bool] = None
    
    source: Optional[str] = None
    
    occurred_after: Optional[date] = None
    occurred_before: Optional[date] = None
    
    order_by: str = Field(default="occurred_at", description="排序字段")
    order_dir: str = Field(default="desc", description="排序方向")
    
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
