"""
驾驶舱 Schema

驾驶舱 API 的 Pydantic 模型。
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============ 管理概览 Schema ============
class DashboardSummary(BaseModel):
    """管理概览 Schema"""
    total_projects: int = Field(..., description="项目总数")
    in_progress_projects: int = Field(..., description="进行中项目")
    risk_projects: int = Field(..., description="风险项目")
    monthly_acceptance_projects: int = Field(..., description="本月验收项目")
    monthly_new_projects: int = Field(..., description="本月新增项目")
    
    # 反直觉指标
    zombie_projects: int = Field(..., description="僵尸项目数（30天无活动）")
    fake_progress_projects: int = Field(..., description="假性推进项目数")
    inactive_channels: int = Field(..., description="沉睡渠道数（60天无活动）")


# ============ 阶段分布 Schema ============
class StageDistributionItem(BaseModel):
    """阶段分布项 Schema"""
    stage: str = Field(..., description="阶段名称")
    count: int = Field(..., description="项目数量")
    percentage: float = Field(..., description="占比百分比")


class StageDistribution(BaseModel):
    """阶段分布 Schema"""
    items: List[StageDistributionItem] = Field(..., description="阶段分布列表")
    total: int = Field(..., description="总项目数")


# ============ 风险项目 TOP10 Schema ============
class RiskProjectItem(BaseModel):
    """风险项目项 Schema"""
    project_id: UUID
    project_name: str
    current_stage: str
    blocker: str = Field(..., description="卡点描述")
    days_stuck: int = Field(..., description="停留天数")
    owner_name: str
    risk_level: str


# ============ 国家分布 Schema ============
class CountryDistributionItem(BaseModel):
    """国家分布项 Schema"""
    country: str = Field(..., description="国家名称")
    project_count: int = Field(..., description="项目数量")
    total_amount: float = Field(..., description="总金额")
    risk_count: int = Field(..., description="风险项目数")


# ============ 渠道贡献分析 Schema ============
class ChannelContributionItem(BaseModel):
    """渠道贡献项 Schema"""
    channel_id: UUID
    channel_name: str
    project_count: int = Field(..., description="项目数量")
    total_amount: float = Field(..., description="成交金额")
    bid_win_rate: float = Field(..., description="中标率")
    poc_success_rate: float = Field(..., description="POC成功率")


# ============ 健康度分布 Schema ============
class HealthDistributionItem(BaseModel):
    """健康度分布项 Schema"""
    health_status: str = Field(..., description="健康度")
    count: int = Field(..., description="项目数量")
    percentage: float = Field(..., description="占比百分比")


# ============ 预警统计 Schema ============
class WarningStatsItem(BaseModel):
    """预警统计项 Schema"""
    severity: str = Field(..., description="严重等级")
    count: int = Field(..., description="预警数量")
    unhandled_count: int = Field(..., description="未处理数量")


# ============ 项目趋势 Schema ============
class ProjectTrendItem(BaseModel):
    """项目趋势项 Schema"""
    month: str = Field(..., description="月份（YYYY-MM）")
    new_projects: int = Field(..., description="新增项目数")
    accepted_projects: int = Field(..., description="验收项目数")
    total_amount: float = Field(..., description="成交金额")


# ============ 战术层 - 验收超时项目 Schema ============
class OverdueProjectItem(BaseModel):
    """验收超时项目 Schema"""
    project_id: UUID
    project_name: str
    current_stage: str
    days_overdue: int = Field(..., description="超时天数")
    owner_name: Optional[str] = None
    planned_acceptance: Optional[datetime] = None


# ============ 战术层 - 渠道沉没预警 Schema ============
class SunkChannelItem(BaseModel):
    """渠道沉没预警 Schema"""
    channel_id: UUID
    channel_name: str
    country: Optional[str] = None
    days_since_last_contact: int = Field(..., description="失联天数")
    total_projects: int = Field(..., description="历史项目数")
    last_contact_date: Optional[datetime] = None


# ============ 执行层 - 今日需跟进项目 Schema ============
class TodayFollowupItem(BaseModel):
    """今日需跟进项目 Schema"""
    project_id: UUID
    project_name: str
    next_action: str = Field(..., description="下一步动作")
    priority: str = Field(..., description="优先级 high/medium/low")
    owner_name: Optional[str] = None


# ============ 执行层 - 等待客户反馈超时 Schema ============
class WaitingTooLongItem(BaseModel):
    """等待客户反馈超时 Schema"""
    project_id: UUID
    project_name: str
    next_action: str = Field(..., description="等待事项")
    days_waiting: int = Field(..., description="等待天数")
