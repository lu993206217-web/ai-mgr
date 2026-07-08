"""
系统配置 Schema

驾驶舱阈值配置和系统通用配置的 Pydantic 模型。
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============ 驾驶舱阈值配置 Schema ============
class DashboardThresholds(BaseModel):
    """驾驶舱阈值配置"""
    # 战略层
    zombie_project_days: int = Field(30, ge=1, description="僵尸项目天数阈值（多少天无活动算僵尸项目）")
    fake_progress_count: int = Field(3, ge=2, description="假性推进连续活动次数")
    sunk_channel_days: int = Field(60, ge=1, description="沉没渠道天数阈值（多少天无联系算沉没）")

    # 战术层
    overdue_acceptance_days: int = Field(0, ge=0, description="验收超时起始天数（已超过计划验收日期）")
    sunk_channel_warning_days: int = Field(90, ge=1, description="战术层渠道沉没预警天数")

    # 执行层
    waiting_too_long_days: int = Field(0, ge=0, description="等待客户反馈超时起始天数")
    today_followup_limit: int = Field(10, ge=1, le=50, description="今日跟进项目数限制")

    # 阶段流转阈值
    poc_overdue_days: int = Field(60, ge=1, description="POC阶段超时天数")
    acceptance_overdue_days: int = Field(30, ge=1, description="验收阶段超时天数")
    acceptance_plan_overdue_days: int = Field(180, ge=1, description="计划验收超期天数（生成长期未验收预警）")

    # 预警冷却期
    no_activity_warning_days: int = Field(7, ge=1, description="无活动预警天数")
    quote_no_progress_days: int = Field(90, ge=1, description="报价后无进展预警天数")

    updated_at: Optional[datetime] = None


class DashboardThresholdsUpdate(BaseModel):
    """驾驶舱阈值更新"""
    zombie_project_days: Optional[int] = Field(None, ge=1)
    fake_progress_count: Optional[int] = Field(None, ge=2)
    sunk_channel_days: Optional[int] = Field(None, ge=1)
    overdue_acceptance_days: Optional[int] = Field(None, ge=0)
    sunk_channel_warning_days: Optional[int] = Field(None, ge=1)
    waiting_too_long_days: Optional[int] = Field(None, ge=0)
    today_followup_limit: Optional[int] = Field(None, ge=1, le=50)
    poc_overdue_days: Optional[int] = Field(None, ge=1)
    acceptance_overdue_days: Optional[int] = Field(None, ge=1)
    acceptance_plan_overdue_days: Optional[int] = Field(None, ge=1)
    no_activity_warning_days: Optional[int] = Field(None, ge=1)
    quote_no_progress_days: Optional[int] = Field(None, ge=1)


# ============ 预警规则配置 Schema ============
class WarningRuleThresholds(BaseModel):
    """预警规则配置"""
    rule_code: str = Field(..., description="规则代码")
    rule_name: str = Field(..., description="规则名称")
    rule_type: str = Field(..., description="规则类型")
    description: Optional[str] = None
    threshold_days: int = Field(..., ge=1, description="触发阈值（天数）")
    severity: str = Field(..., description="严重等级")
    is_active: bool = Field(True, description="是否启用")
    cooldown_days: int = Field(1, ge=1, description="冷却期天数")
    target_type: str = Field(..., description="目标类型: project/channel/quote")
    target_filter: Optional[str] = Field(None, description="目标过滤条件")


class WarningRuleThresholdsUpdate(BaseModel):
    """预警规则更新"""
    rule_name: Optional[str] = None
    description: Optional[str] = None
    threshold_days: Optional[int] = Field(None, ge=1)
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    cooldown_days: Optional[int] = Field(None, ge=1)
    target_filter: Optional[str] = None
