# schemas 包初始化
# 导出所有 Schema 类

from app.schemas.user import User, UserCreate, LoginRequest, Token
from app.schemas.project import Project, ProjectCreate, ProjectUpdate, ProjectQueryParams
from app.schemas.channel import Channel, ChannelCreate, ChannelUpdate
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate
from app.schemas.activity_log import ActivityLog, ActivityLogCreate, ActivityLogUpdate, ActivityLogQueryParams
from app.schemas.quote import Quote, QuoteCreate, QuoteUpdate
from app.schemas.warning import (
    WarningRule, WarningRuleCreate, WarningRuleUpdate,
    WarningInstance, WarningInstanceHandle, WarningInstanceQueryParams
)
from app.schemas.dashboard import (
    DashboardSummary, StageDistribution, RiskProjectItem,
    CountryDistributionItem, ChannelContributionItem,
    HealthDistributionItem, WarningStatsItem
)
from app.schemas.common import PaginationParams, PaginatedResponse, Response

__all__ = [
    "User", "UserCreate", "LoginRequest", "Token",
    "Project", "ProjectCreate", "ProjectUpdate", "ProjectQueryParams",
    "Channel", "ChannelCreate", "ChannelUpdate",
    "Customer", "CustomerCreate", "CustomerUpdate",
    "ActivityLog", "ActivityLogCreate", "ActivityLogUpdate", "ActivityLogQueryParams",
    "Quote", "QuoteCreate", "QuoteUpdate",
    "WarningRule", "WarningRuleCreate", "WarningRuleUpdate",
    "WarningInstance", "WarningInstanceHandle", "WarningInstanceQueryParams",
    "DashboardSummary", "StageDistribution", "RiskProjectItem",
    "CountryDistributionItem", "ChannelContributionItem",
    "HealthDistributionItem", "WarningStatsItem",
    "PaginationParams", "PaginatedResponse", "Response",
]
