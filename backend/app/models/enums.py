"""
枚举类型定义

系统中使用的所有枚举类型。
"""
from enum import Enum


class ProjectStage(str, Enum):
    """项目阶段枚举"""
    PRE_SALE = "售前"
    POC = "POC"
    BIDDING = "投标"
    IMPLEMENTATION = "实施"
    ACCEPTANCE = "验收"
    OPERATION = "运维"
    ARCHIVED = "归档"


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    IN_PROGRESS = "进行中"
    ACCEPTED = "已验收"
    TERMINATED = "已终止"
    ARCHIVED = "已归档"


class HealthStatus(str, Enum):
    """健康度枚举"""
    HEALTHY = "健康"
    ATTENTION = "关注"
    RISK = "风险"
    SERIOUS_RISK = "严重风险"


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class ProjectSourceType(str, Enum):
    """项目来源类型枚举"""
    CHANNEL_DIRECT = "渠道直转"
    OPPORTUNITY = "商机转项目"
    POC_TO_PROJECT = "POC转项目"
    DIRECT_PURCHASE = "直接采购"
    BIDDING = "招投标"
    INTERNAL = "内部项目"


class ActivityType(str, Enum):
    """活动类型枚举"""
    PROGRESS_UPDATE = "进展更新"
    RISK_REPORT = "风险上报"
    MILESTONE_COMPLETE = "里程碑完成"
    BLOCKER_WAITING = "阻塞等待"
    OTHER = "其他"


class NextAction(str, Enum):
    """下一步动作枚举"""
    WAITING_CUSTOMER = "等待客户反馈"
    WAITING_INTERNAL = "等待内部审批"
    WAITING_CONTRACT = "等待合同签订"
    WAITING_ACCEPTANCE = "等待验收"
    OTHER = "其他"


class ActivitySource(str, Enum):
    """活动来源枚举"""
    DAILY_REPORT = "日报"
    WEEKLY_REPORT = "周报"
    EMAIL = "邮件"
    MEETING = "会议"
    FILE = "文件"
    MANUAL = "手工录入"
    SYSTEM = "系统生成"


class WarningSeverity(str, Enum):
    """预警严重等级枚举"""
    INFO = "提示"
    ATTENTION = "关注"
    WARNING = "警告"
    CRITICAL = "严重"


class WarningStatus(str, Enum):
    """预警状态枚举"""
    ACTIVE = "活跃"
    HANDLED = "已处理"
    IGNORED = "已忽略"


class ChannelCooperationStatus(str, Enum):
    """渠道合作状态枚举"""
    ACTIVE = "活跃"
    PAUSED = "暂停"
    TERMINATED = "终止"
