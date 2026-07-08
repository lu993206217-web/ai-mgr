"""
渠道 Schema

渠道管理的 Pydantic 模型。
"""
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


# ============ 基础 Schema ============
class ChannelBase(BaseModel):
    """渠道基础 Schema"""
    channel_name: str = Field(..., min_length=1, max_length=200)
    country: str = Field(..., min_length=1, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=100)
    cooperation_level: Optional[str] = Field(default="普通", max_length=50)
    cooperation_status: str = Field(default="活跃")
    cooperation_start_date: Optional[date] = None


class ChannelCreate(ChannelBase):
    """渠道创建 Schema"""
    pass


class ChannelUpdate(BaseModel):
    """渠道更新 Schema"""
    channel_name: Optional[str] = Field(None, min_length=1, max_length=200)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=100)
    cooperation_level: Optional[str] = Field(None, max_length=50)
    cooperation_status: Optional[str] = None
    cooperation_start_date: Optional[date] = None


class ChannelInDB(ChannelBase):
    """渠道数据库 Schema"""
    id: UUID
    
    total_project_count: int = 0
    total_deal_amount: Optional[Decimal] = None
    bid_win_rate: Optional[Decimal] = None
    last_contact_date: Optional[date] = None
    
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    
    class Config:
        from_attributes = True


class Channel(ChannelInDB):
    """渠道响应 Schema"""
    total_projects: int = 0
    total_amount: Optional[Decimal] = None
