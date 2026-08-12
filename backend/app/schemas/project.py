"""
项目 Schema

项目管理的 Pydantic 模型。
"""
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.activity_presentation import EmailActivityDetail


# ============ 基础 Schema ============
class ProjectBase(BaseModel):
    """项目基础 Schema"""
    project_name: str = Field(..., min_length=1, max_length=200)
    country: str = Field(..., min_length=1, max_length=100)
    customer_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None  # 创建时可空，后端默认当前用户

    project_amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=10)

    source_type: str = Field(..., description="项目来源类型")
    current_stage: str = Field(default="售前", description="当前阶段")

    planned_go_live: Optional[date] = None
    planned_acceptance: Optional[date] = None


class ProjectCreate(ProjectBase):
    """项目创建 Schema"""
    pass


class ProjectUpdate(BaseModel):
    """项目更新 Schema"""
    project_name: Optional[str] = Field(None, min_length=1, max_length=200)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    customer_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    
    project_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    
    current_stage: Optional[str] = None
    
    planned_go_live: Optional[date] = None
    planned_acceptance: Optional[date] = None
    
    health_status: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None


class ProjectInDB(ProjectBase):
    """项目数据库 Schema"""
    id: UUID
    stage_entered_at: datetime
    
    health_status: str
    risk_level: str
    status: str
    
    last_activity_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    
    class Config:
        from_attributes = True


class Project(ProjectInDB):
    """项目响应 Schema"""
    owner_name: Optional[str] = None
    customer_name: Optional[str] = None
    channel_name: Optional[str] = None
    
    activity_count: int = 0
    days_since_last_activity: Optional[int] = None


# ============ 阶段流转 Schema ============
class StageTransitionRequest(BaseModel):
    """阶段流转请求 Schema"""
    target_stage: str = Field(..., description="目标阶段")
    transition_note: Optional[str] = Field(None, max_length=500, description="流转备注")


class ProjectStateEventItem(BaseModel):
    id: UUID
    event_type: str
    from_value: Optional[str] = None
    to_value: str
    note: Optional[str] = None
    source: str
    occurred_at: datetime
    changed_by: Optional[UUID] = None

    class Config:
        from_attributes = True


# ============ 查询参数 Schema ============
class ProjectQueryParams(BaseModel):
    """项目查询参数 Schema"""
    project_name: Optional[str] = None
    country: Optional[str] = None
    customer_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    
    current_stage: Optional[str] = None
    health_status: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None
    
    created_after: Optional[date] = None
    created_before: Optional[date] = None
    
    order_by: str = Field(default="created_at", description="排序字段")
    order_dir: str = Field(default="desc", description="排序方向")
    
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)


# ============ 活动日志 Schema ============
class ActivityLogBase(BaseModel):
    """活动日志基础 Schema"""
    activity_type: str = Field(..., description="活动类型")
    activity_content: str = Field(..., description="活动内容")
    next_action: Optional[str] = Field(None, description="下一步动作")
    next_action_deadline: Optional[date] = None
    blocker_flag: bool = Field(default=False, description="是否阻塞")
    occurred_at: Optional[datetime] = None


class ActivityLogCreate(ActivityLogBase):
    """活动日志创建 Schema"""
    pass


class ActivityLogInDB(ActivityLogBase):
    """活动日志数据库 Schema"""
    id: UUID
    project_id: UUID
    owner_id: UUID
    source: str = "MANUAL"
    source_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ActivityLog(ActivityLogInDB):
    """活动日志响应 Schema"""
    owner_name: Optional[str] = None
    display_title: Optional[str] = None
    display_summary: Optional[str] = None
    email_detail: Optional[EmailActivityDetail] = None


# ============ 项目文件 Schema ============
class ProjectFileBase(BaseModel):
    """项目文件基础 Schema"""
    file_name: str = Field(..., min_length=1, max_length=255, description="文件名称")
    file_category: str = Field(default="其他", max_length=50, description="文件分类")
    file_url: Optional[str] = Field(None, max_length=1000, description="文件链接或存放路径")
    file_source: Optional[str] = Field(None, max_length=100, description="文件来源")
    owner_party: Optional[str] = Field(None, max_length=50, description="归属方")
    description: Optional[str] = Field(None, max_length=1000, description="备注")


class ProjectFileCreate(ProjectFileBase):
    """项目文件创建 Schema"""
    pass


class ProjectFileUpdate(BaseModel):
    """项目文件更新 Schema"""
    file_name: Optional[str] = Field(None, min_length=1, max_length=255)
    file_category: Optional[str] = Field(None, max_length=50)
    file_url: Optional[str] = Field(None, max_length=1000)
    file_source: Optional[str] = Field(None, max_length=100)
    owner_party: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)


class ProjectFileInDB(ProjectFileBase):
    """项目文件数据库 Schema"""
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    class Config:
        from_attributes = True


class ProjectFile(ProjectFileInDB):
    """项目文件响应 Schema"""
    created_by_name: Optional[str] = None
