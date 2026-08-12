# models 包初始化
# 导出所有模型类

from app.models.user import User
from app.models.project import Project
from app.models.channel import Channel
from app.models.customer import Customer
from app.models.activity_log import ActivityLog
from app.models.project_file import ProjectFile
from app.models.email_intelligence import EmailMessage, EmailAttachment, EmailMatchAudit
from app.models.daily_report import (
    DailyReportBinding,
    DailyReportProjectAlias,
    DailyReportUnmatchedProject,
    DailyReportActivityMapping,
    DailyReportSyncRun,
    DailyReportRawEntry,
)
from app.models.quote import Quote
from app.models.warning import WarningRule, WarningInstance
from app.models.project_intelligence import ProjectStateEvent, ProjectIntelligenceSnapshot
from app.models.overseas_performance import OverseasPerformanceConfig, OverseasPerformanceReport
from app.models.workflow import (
    WorkflowItem, WorkflowEvidence, WorkflowStateEvent, WorkflowAlert,
    WorkflowAutomationTask, WorkflowAutomationRun,
)
from app.models.enums import (
    ProjectStage, ProjectStatus, HealthStatus, RiskLevel, ProjectSourceType,
    ActivityType, NextAction, ActivitySource,
    WarningSeverity, WarningStatus,
    ChannelCooperationStatus,
)

__all__ = [
    "User", "Project", "Channel", "Customer", "ActivityLog", "ProjectFile",
    "EmailMessage", "EmailAttachment", "EmailMatchAudit",
    "DailyReportBinding", "DailyReportProjectAlias", "DailyReportUnmatchedProject",
    "DailyReportActivityMapping", "DailyReportSyncRun",
    "DailyReportRawEntry",
    "Quote",
    "WarningRule", "WarningInstance",
    "ProjectStateEvent", "ProjectIntelligenceSnapshot",
    "OverseasPerformanceConfig", "OverseasPerformanceReport",
    "WorkflowItem", "WorkflowEvidence", "WorkflowStateEvent", "WorkflowAlert",
    "WorkflowAutomationTask", "WorkflowAutomationRun",
    "ProjectStage", "ProjectStatus", "HealthStatus", "RiskLevel", "ProjectSourceType",
    "ActivityType", "NextAction", "ActivitySource",
    "WarningSeverity", "WarningStatus",
    "ChannelCooperationStatus",
]
