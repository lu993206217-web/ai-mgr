"""
预警 Schema

预警规则引擎的 Pydantic 模型。
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ============ 预警规则 Schema ============
class WarningRuleBase(BaseModel):
    """预警规则基础 Schema"""
    rule_name: str = Field(..., min_length=1, max_length=100)
    rule_code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    
    conditions: dict = Field(..., description="规则条件（JSON 格式）")
    severity: str = Field(..., description="严重等级")
    notify_targets: List[str] = Field(..., description="通知目标")
    notify_channels: List[str] = Field(..., description="通知渠道")
    cooldown_days: int = Field(default=7, ge=0)
    
    is_active: bool = Field(default=True)


class WarningRuleCreate(WarningRuleBase):
    """预警规则创建 Schema"""
    pass


class WarningRuleUpdate(BaseModel):
    """预警规则更新 Schema"""
    rule_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    conditions: Optional[dict] = None
    severity: Optional[str] = None
    notify_targets: Optional[List[str]] = None
    notify_channels: Optional[List[str]] = None
    cooldown_days: Optional[int] = Field(None, ge=0)
    
    is_active: Optional[bool] = None


class WarningRuleInDB(WarningRuleBase):
    """预警规则数据库 Schema"""
    id: UUID
    
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    
    class Config:
        from_attributes = True


class WarningRule(WarningRuleInDB):
    """预警规则响应 Schema"""
    instance_count: int = 0


# ============ 预警实例 Schema ============
class WarningInstanceBase(BaseModel):
    """预警实例基础 Schema"""
    rule_id: UUID
    project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    
    severity: str = Field(..., description="严重等级")
    status: str = Field(default="活跃", description="预警状态")
    message: str = Field(..., min_length=1, max_length=1000)


class WarningInstanceHandle(BaseModel):
    """预警实例处理 Schema"""
    status: str = Field(..., description="处理状态（已处理/已忽略）")
    handle_note: Optional[str] = Field(None, max_length=500)


class WarningInstanceInDB(WarningInstanceBase):
    """预警实例数据库 Schema"""
    id: UUID
    
    handled_by: Optional[UUID] = None
    handled_at: Optional[datetime] = None
    handle_note: Optional[str] = None
    
    notified_at: Optional[datetime] = None
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class WarningInstance(WarningInstanceInDB):
    """预警实例响应 Schema"""
    rule_name: Optional[str] = None
    project_name: Optional[str] = None
    channel_name: Optional[str] = None
    handled_by_name: Optional[str] = None


# ============ 查询参数 Schema ============
class WarningInstanceQueryParams(BaseModel):
    """预警实例查询参数 Schema"""
    rule_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    
    severity: Optional[str] = None
    status: Optional[str] = None
    
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    order_by: str = Field(default="created_at", description="排序字段")
    order_dir: str = Field(default="desc", description="排序方向")
    
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
