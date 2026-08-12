"""
驾驶舱 API 路由

管理概览、阶段分布、风险项目、国家分布、渠道贡献等分析接口。
SQLite 兼容版本。
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from email.utils import parseaddr
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.core.security import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.project import Project
from app.models.channel import Channel
from app.models.activity_log import ActivityLog
from app.models.warning import WarningInstance
from app.services.mail_runtime_config import get_dingtalk_mail_config
from app.models.daily_report import DailyReportRawEntry, DailyReportSyncRun
from app.models.email_intelligence import EmailMessage
from app.models.project_intelligence import ProjectIntelligenceSnapshot
from app.models.enums import (
    HealthStatus,
    NextAction,
    ProjectStatus,
)
from app.api.v1.config import get_thresholds
from app.schemas.dashboard import (
    DashboardSummary,
    StageDistribution,
    StageDistributionItem,
    RiskProjectItem,
    CountryDistributionItem,
    ChannelContributionItem,
    HealthDistributionItem,
    WarningStatsItem,
    OverdueProjectItem,
    SunkChannelItem,
    AttentionProjectItem,
    TodayFollowupItem,
    WaitingTooLongItem,
    IntelligenceTrendItem,
    WaitingEmailThreadItem,
    ManagementInsightItem,
)
from app.schemas.common import Response

router = APIRouter(tags=["驾驶舱"])


def _days_since(value: datetime | date | None, now: datetime | None = None) -> int | None:
    """兼容 SQLite 无时区 datetime 的天数计算。"""
    if value is None:
        return None
    now = now or datetime.now()
    if isinstance(value, date) and not isinstance(value, datetime):
        return max((now.date() - value).days, 0)
    comparable_now = now
    if value.tzinfo is not None:
        comparable_now = datetime.now(value.tzinfo)
    elif comparable_now.tzinfo is not None:
        comparable_now = comparable_now.replace(tzinfo=None)
    return max((comparable_now - value).days, 0)


def _active_projects(db: Session) -> list[Project]:
    return db.query(Project).filter(Project.status != ProjectStatus.ARCHIVED).all()


def _health(project: Project) -> HealthStatus:
    try:
        return project.health_status_computed
    except Exception:
        return project.health_status


def _effective_channel_contact(db: Session, channel: Channel) -> date:
    """优先使用人工联系时间，其次使用渠道关联项目的真实活动时间，最后才用创建时间。"""
    latest_activity = (
        db.query(func.max(ActivityLog.occurred_at))
        .outerjoin(Project, ActivityLog.project_id == Project.id)
        .filter(or_(ActivityLog.channel_id == channel.id, Project.channel_id == channel.id))
        .scalar()
    )
    candidates: list[date] = []
    if channel.last_contact_date:
        candidates.append(channel.last_contact_date)
    if latest_activity:
        candidates.append(latest_activity.date())
    if candidates:
        return max(candidates)
    return channel.created_at.date()


def _project_risk_reason(project: Project, now: datetime) -> str:
    blocking = next(
        (activity for activity in sorted(project.activities, key=lambda item: item.occurred_at, reverse=True)
         if activity.blocker_flag),
        None,
    )
    if blocking:
        summary = " ".join((blocking.activity_content or "").split())
        return f"阻塞：{summary[:80]}"
    if not project.last_activity_at:
        days = _days_since(project.created_at, now) or 0
        return f"创建后 {days} 天尚无有效活动"
    days = _days_since(project.last_activity_at, now) or 0
    return f"已有 {days} 天无有效活动"


def _mail_account_addresses() -> set[str]:
    dingtalk_config = get_dingtalk_mail_config()
    return {
        value.strip().casefold()
        for value in (dingtalk_config.account_email, settings.GMAIL_ACCOUNT_EMAIL)
        if value and value.strip()
    }


def _mail_account_domains() -> set[str]:
    return {address.rsplit("@", 1)[1] for address in _mail_account_addresses() if "@" in address}


def _is_internal_sender(address: str, accounts: set[str], domains: set[str]) -> bool:
    normalized = parseaddr(address or "")[1].casefold()
    if normalized in accounts:
        return True
    if "@" not in normalized:
        return False
    domain = normalized.rsplit("@", 1)[1]
    # 公共邮箱域名只能按具体账号判断，避免把客户的 Gmail 当作内部邮件。
    if domain in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com"}:
        return False
    return domain in domains


def _waiting_email_threads(db: Session, threshold_days: int) -> list[WaitingEmailThreadItem]:
    accounts = _mail_account_addresses()
    domains = _mail_account_domains()
    if not accounts:
        return []
    grouped: dict[str, list[EmailMessage]] = {}
    messages = db.query(EmailMessage).filter(
        EmailMessage.project_id.isnot(None)
    ).order_by(EmailMessage.received_at.asc()).all()
    for message in messages:
        thread_key = message.thread_id or message.internet_message_id or str(message.id)
        key = f"{message.provider}:{thread_key}"
        grouped.setdefault(key, []).append(message)

    today = date.today()
    result: list[WaitingEmailThreadItem] = []
    for _, thread_messages in grouped.items():
        latest = thread_messages[-1]
        if not _is_internal_sender(latest.sender, accounts, domains):
            continue
        recipients = json.loads(latest.recipients_json or "[]") + json.loads(latest.cc_json or "[]")
        external_recipients = [
            address for address in recipients
            if not _is_internal_sender(address, accounts, domains)
        ]
        if not external_recipients:
            continue
        waiting_days = max((today - latest.received_at.date()).days, 0)
        if waiting_days < threshold_days:
            continue
        result.append(WaitingEmailThreadItem(
            email_id=latest.id,
            thread_id=latest.thread_id or latest.internet_message_id or str(latest.id),
            project_id=latest.project_id,
            project_name=latest.project.project_name,
            subject=latest.subject,
            sender=latest.sender,
            sent_at=latest.received_at,
            waiting_days=waiting_days,
            recipients=external_recipients,
        ))
    result.sort(key=lambda item: item.waiting_days, reverse=True)
    return result


# ============ 管理概览接口 ============
@router.get("/summary", response_model=Response[DashboardSummary])
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    获取管理概览数据

    包含：项目总数、进行中、风险项目、本月验收、本月新增、僵尸项目等。
    """
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    thresholds = get_thresholds()
    projects = _active_projects(db)
    total_projects = len(projects)
    in_progress = sum(1 for project in projects if project.status == ProjectStatus.IN_PROGRESS)
    risk_projects = sum(
        1 for project in projects if _health(project) in (HealthStatus.RISK, HealthStatus.SERIOUS_RISK)
    )

    # 只能把状态已经是“已验收”且本月发生更新的项目计入；普通资料更新不能再冒充验收。
    monthly_accepted = db.query(func.count(Project.id)).filter(
        Project.status == ProjectStatus.ACCEPTED,
        Project.updated_at >= month_start,
    ).scalar() or 0
    monthly_new = sum(1 for project in projects if project.created_at >= month_start)

    zombie_days = thresholds["zombie_project_days"]
    zombie_projects = sum(
        1
        for project in projects
        if (_days_since(project.last_activity_at or project.created_at, now) or 0) > zombie_days
    )

    fake_progress = 0
    fake_progress_count = thresholds["fake_progress_count"]
    for project in projects:
        recent = sorted(project.activities, key=lambda item: item.occurred_at, reverse=True)[:fake_progress_count]
        if len(recent) == fake_progress_count and all(
            activity.next_action == NextAction.WAITING_CUSTOMER for activity in recent
        ):
            fake_progress += 1

    channels = db.query(Channel).all()
    inactive_channels = sum(
        1
        for channel in channels
        if (_days_since(_effective_channel_contact(db, channel), now) or 0) > thresholds["sunk_channel_days"]
    )

    active_ids = {project.id for project in projects}
    covered_project_ids = {
        project_id
        for (project_id,) in db.query(ActivityLog.project_id)
        .filter(ActivityLog.project_id.isnot(None))
        .distinct()
        .all()
        if project_id in active_ids
    }
    coverage_percentage = round(len(covered_project_ids) / total_projects * 100, 1) if total_projects else 0
    latest_sync = db.query(DailyReportSyncRun).order_by(DailyReportSyncRun.started_at.desc()).first()

    summary = DashboardSummary(
        total_projects=total_projects,
        in_progress_projects=in_progress,
        risk_projects=risk_projects,
        monthly_acceptance_projects=monthly_accepted,
        monthly_new_projects=monthly_new,
        zombie_projects=zombie_projects,
        fake_progress_projects=fake_progress,
        inactive_channels=inactive_channels,
        latest_activity_at=db.query(func.max(ActivityLog.occurred_at)).scalar(),
        latest_ingestion_at=db.query(func.max(ActivityLog.created_at)).scalar(),
        latest_daily_sync_at=(latest_sync.finished_at or latest_sync.started_at) if latest_sync else None,
        latest_daily_sync_status=latest_sync.status if latest_sync else None,
        activity_covered_projects=len(covered_project_ids),
        activity_coverage_percentage=coverage_percentage,
        daily_report_raw_count=db.query(func.count(DailyReportRawEntry.id)).scalar() or 0,
        daily_report_imported_count=db.query(func.count(DailyReportRawEntry.id)).filter(
            DailyReportRawEntry.activity_log_id.isnot(None)
        ).scalar() or 0,
        daily_report_pending_match_count=db.query(func.count(DailyReportRawEntry.id)).filter(
            DailyReportRawEntry.analysis_status == "待人工匹配"
        ).scalar() or 0,
        email_message_count=db.query(func.count(EmailMessage.id)).scalar() or 0,
    )

    return Response.success(data=summary, message="获取成功")


# ============ 阶段分布接口 ============
@router.get("/stage-distribution", response_model=Response[StageDistribution])
async def get_stage_distribution(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目阶段分布"""
    from app.models.enums import ProjectStage

    projects = _active_projects(db)
    total = len(projects)

    items = []
    for stage in ProjectStage:
        count = sum(1 for project in projects if project.current_stage == stage)
        percentage = round(count / total * 100, 2) if total > 0 else 0
        items.append(StageDistributionItem(
            stage=stage.value,
            count=count,
            percentage=percentage
        ))

    return Response.success(
        data=StageDistribution(items=items, total=total),
        message="获取成功"
    )


# ============ 风险项目 TOP10 接口 ============
@router.get("/risk-top10", response_model=Response[list[RiskProjectItem]])
async def get_risk_top10(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取风险项目 TOP10"""
    now = datetime.now()

    projects = [
        project
        for project in _active_projects(db)
        if project.status == ProjectStatus.IN_PROGRESS
        and _health(project) in (HealthStatus.RISK, HealthStatus.SERIOUS_RISK)
    ]
    severity_order = {HealthStatus.SERIOUS_RISK: 2, HealthStatus.RISK: 1}
    projects.sort(
        key=lambda project: (
            severity_order.get(_health(project), 0),
            _days_since(project.last_activity_at or project.created_at, now) or 0,
        ),
        reverse=True,
    )

    result = []
    for project in projects[:10]:
        days_stuck = 0
        if project.stage_entered_at:
            days_stuck = (now - project.stage_entered_at).days

        result.append(RiskProjectItem(
            project_id=str(project.id),
            project_name=project.project_name,
            country=project.country,
            current_stage=project.current_stage,
            blocker=_project_risk_reason(project, now),
            days_stuck=days_stuck,
            owner_name=project.owner.full_name if project.owner else None,
            risk_level=_health(project).value,
        ))
    return Response.success(data=result, message="获取成功")


# ============ 战术层 - 项目关注矩阵接口 ============
@router.get("/attention-projects", response_model=Response[list[AttentionProjectItem]])
async def get_attention_projects(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """按健康度、活动时效和阻塞证据输出需要管理介入的项目。"""
    now = datetime.now()
    severity_order = {
        HealthStatus.SERIOUS_RISK: 3,
        HealthStatus.RISK: 2,
        HealthStatus.ATTENTION: 1,
        HealthStatus.HEALTHY: 0,
    }
    result: list[AttentionProjectItem] = []
    for project in _active_projects(db):
        health = _health(project)
        latest_activity = max(project.activities, key=lambda item: item.occurred_at, default=None)
        action_activity = next(
            (
                item for item in sorted(project.activities, key=lambda value: value.occurred_at, reverse=True)
                if item.next_action
            ),
            None,
        )
        has_blocker = bool(latest_activity and latest_activity.blocker_flag)
        if health == HealthStatus.HEALTHY and not has_blocker:
            continue
        result.append(AttentionProjectItem(
            project_id=project.id,
            project_name=project.project_name,
            country=project.country,
            current_stage=project.current_stage,
            health_status=health.value,
            stage_days=_days_since(project.stage_entered_at, now) or 0,
            inactivity_days=_days_since(project.last_activity_at or project.created_at, now) or 0,
            attention_reason=_project_risk_reason(project, now),
            latest_activity_at=latest_activity.occurred_at if latest_activity else None,
            latest_activity_source=latest_activity.source.value if latest_activity else None,
            next_action=action_activity.next_action.value if action_activity and action_activity.next_action else None,
            next_action_deadline=action_activity.next_action_deadline if action_activity else None,
            owner_name=project.owner.full_name if project.owner else None,
        ))
    result.sort(
        key=lambda item: (
            severity_order.get(HealthStatus(item.health_status), 0),
            item.inactivity_days,
        ),
        reverse=True,
    )
    return Response.success(data=result[:30], message="获取成功")


# ============ 国家分布接口 ============
@router.get("/country-distribution", response_model=Response[list[CountryDistributionItem]])
async def get_country_distribution(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取国家分布统计"""
    grouped: dict[str, dict[str, float | int]] = {}
    for project in _active_projects(db):
        country = project.country or "未知"
        item = grouped.setdefault(country, {"project_count": 0, "total_amount": 0.0, "risk_count": 0})
        item["project_count"] += 1
        item["total_amount"] += float(project.project_amount or 0)
        if _health(project) in (HealthStatus.RISK, HealthStatus.SERIOUS_RISK):
            item["risk_count"] += 1

    result = [
        CountryDistributionItem(country=country, **stats)
        for country, stats in sorted(grouped.items(), key=lambda entry: entry[1]["project_count"], reverse=True)
    ]

    return Response.success(data=result, message="获取成功")


# ============ 渠道贡献分析接口 ============
@router.get("/channel-contribution", response_model=Response[list[ChannelContributionItem]])
async def get_channel_contribution(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取渠道贡献分析"""
    channels = db.query(Channel).all()

    result = []
    for channel in channels:
        project_count = db.query(func.count(Project.id)).filter(
            Project.channel_id == channel.id
        ).scalar() or 0

        total_amount = db.query(func.sum(Project.project_amount)).filter(
            Project.channel_id == channel.id,
            Project.status == ProjectStatus.ACCEPTED,
        ).scalar() or 0

        result.append(ChannelContributionItem(
            channel_id=str(channel.id),
            channel_name=channel.channel_name,
            project_count=project_count,
            total_amount=float(total_amount or 0),
            bid_win_rate=float(channel.bid_win_rate or 0),
            poc_success_rate=0.0,
        ))

    result.sort(key=lambda item: item.project_count, reverse=True)
    return Response.success(data=result[:10], message="获取成功")


# ============ 健康度分布接口 ============
@router.get("/health-distribution", response_model=Response[list[HealthDistributionItem]])
async def get_health_distribution(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目健康度分布"""
    projects = _active_projects(db)
    total = len(projects)
    counts = {health: 0 for health in HealthStatus}
    for project in projects:
        counts[_health(project)] += 1

    items = []
    for health in HealthStatus:
        count = counts[health]
        percentage = round(count / total * 100, 2) if total else 0
        items.append(HealthDistributionItem(
            health_status=health.value,
            count=count,
            percentage=percentage
        ))

    return Response.success(data=items, message="获取成功")


# ============ 预警统计接口 ============
@router.get("/warning-stats", response_model=Response[list[WarningStatsItem]])
async def get_warning_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取预警统计"""
    from app.models.enums import WarningSeverity

    items = []
    for severity in WarningSeverity:
        count = db.query(func.count(WarningInstance.id)).filter(
            WarningInstance.severity == severity.value
        ).scalar() or 0

        unhandled_count = db.query(func.count(WarningInstance.id)).filter(
            WarningInstance.severity == severity.value,
            WarningInstance.status == "活跃"
        ).scalar() or 0

        items.append(WarningStatsItem(
            severity=severity.value,
            count=count,
            unhandled_count=unhandled_count,
        ))

    return Response.success(data=items, message="获取成功")


# ============ 近期活动流接口 ============
@router.get("/recent-activities", response_model=Response[list[dict]])
async def get_recent_activities(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取近期活动流"""
    activities = (
        db.query(ActivityLog)
        .order_by(desc(ActivityLog.occurred_at))
        .limit(limit)
        .all()
    )

    result = []
    for activity in activities:
        project_name = activity.project.project_name if activity.project else None
        result.append({
            "id": str(activity.id),
            "project_id": str(activity.project_id) if activity.project_id else None,
            "project_name": project_name,
            "activity_type": activity.activity_type,
            "source": activity.source,
            "activity_content": activity.activity_content,
            "owner_name": activity.owner.full_name if activity.owner else None,
            "occurred_at": activity.occurred_at.isoformat() if activity.occurred_at else None,
        })

    return Response.success(data=result, message="获取成功")


# ============ 战术层 - 验收超时项目接口 ============
@router.get("/overdue-projects", response_model=Response[list[OverdueProjectItem]])
async def get_overdue_projects(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取验收超时项目（已超过计划验收日期且未验收）"""
    today = date.today()
    threshold_days = get_thresholds()["overdue_acceptance_days"]
    projects = [
        project for project in _active_projects(db)
        if project.planned_acceptance
        and project.status not in (ProjectStatus.ACCEPTED, ProjectStatus.TERMINATED)
        and (today - project.planned_acceptance).days > threshold_days
    ]

    result = []
    for project in projects[:20]:
        # 计算超时天数
        days_overdue = 0
        if project.planned_acceptance:
            try:
                if isinstance(project.planned_acceptance, str):
                    planned_date = datetime.strptime(project.planned_acceptance[:10], "%Y-%m-%d").date()
                else:
                    planned_date = project.planned_acceptance
                days_overdue = (today - planned_date).days
            except Exception:
                days_overdue = 0

        result.append(OverdueProjectItem(
            project_id=str(project.id),
            project_name=project.project_name,
            current_stage=project.current_stage or "未知",
            days_overdue=max(days_overdue, 0),
            owner_name=project.owner.full_name if project.owner else None,
            planned_acceptance=project.planned_acceptance if project.planned_acceptance else None,
        ))

    result.sort(key=lambda x: x.days_overdue, reverse=True)
    return Response.success(data=result, message="获取成功")


# ============ 战术层 - 渠道沉没预警接口 ============
@router.get("/sunk-channels", response_model=Response[list[SunkChannelItem]])
async def get_sunk_channels(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取沉没渠道（90天无联系）"""
    today = date.today()
    threshold_days = get_thresholds()["sunk_channel_warning_days"]
    channels = db.query(Channel).all()

    result = []
    for channel in channels:
        effective_contact = _effective_channel_contact(db, channel)
        days_since_last_contact = max((today - effective_contact).days, 0)
        if days_since_last_contact <= threshold_days:
            continue

        # 统计历史项目数
        total_projects = db.query(func.count(Project.id)).filter(
            Project.channel_id == channel.id
        ).scalar() or 0

        result.append(SunkChannelItem(
            channel_id=str(channel.id),
            channel_name=channel.channel_name,
            country=channel.country,
            days_since_last_contact=days_since_last_contact,
            total_projects=total_projects,
            last_contact_date=effective_contact,
        ))

    result.sort(key=lambda x: x.days_since_last_contact, reverse=True)
    return Response.success(data=result, message="获取成功")


# ============ 执行层 - 今日需跟进项目接口 ============
@router.get("/today-followups", response_model=Response[list[TodayFollowupItem]])
async def get_today_followups(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取今日需跟进项目（有 next_action 字段且进行中的项目）"""
    # 查询进行中且有下一步动作的项目
    activities = db.query(ActivityLog).filter(
        ActivityLog.next_action.isnot(None),
        ActivityLog.next_action != "",
    ).order_by(desc(ActivityLog.occurred_at)).limit(50).all()

    result = []
    followup_limit = get_thresholds()["today_followup_limit"]
    seen_projects = set()
    for activity in activities:
        if not activity.project_id or str(activity.project_id) in seen_projects:
            continue

        project = activity.project
        if not project or project.status in (ProjectStatus.ACCEPTED, ProjectStatus.ARCHIVED, ProjectStatus.TERMINATED):
            continue

        seen_projects.add(str(activity.project_id))

        # 根据 risk_level 决定优先级
        priority = "low"
        computed_health = _health(project)
        if computed_health == HealthStatus.SERIOUS_RISK:
            priority = "high"
        elif computed_health in (HealthStatus.RISK, HealthStatus.ATTENTION):
            priority = "medium"

        result.append(TodayFollowupItem(
            project_id=str(project.id),
            project_name=project.project_name,
            next_action=activity.next_action,
            priority=priority,
            owner_name=project.owner.full_name if project.owner else None,
        ))

        if len(result) >= followup_limit:
            break

    return Response.success(data=result, message="获取成功")


# ============ 执行层 - 等待客户反馈超时接口 ============
@router.get("/waiting-too-long", response_model=Response[list[WaitingTooLongItem]])
async def get_waiting_too_long(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取等待客户反馈超时的项目（有 next_action_deadline 且已超期）"""
    today = date.today()
    threshold_days = get_thresholds()["waiting_too_long_days"]
    cutoff = today - timedelta(days=threshold_days)

    # 查询有下一步动作截止日期且已超期的活动
    activities = db.query(ActivityLog).filter(
        ActivityLog.next_action_deadline.isnot(None),
        ActivityLog.next_action_deadline < cutoff,
    ).order_by(ActivityLog.next_action_deadline).limit(20).all()

    result = []
    seen_projects = set()
    for activity in activities:
        if not activity.project or activity.project_id in seen_projects:
            continue
        seen_projects.add(activity.project_id)

        # 计算等待天数
        days_waiting = 0
        if activity.next_action_deadline:
            try:
                if isinstance(activity.next_action_deadline, str):
                    deadline = datetime.strptime(activity.next_action_deadline[:10], "%Y-%m-%d").date()
                else:
                    deadline = activity.next_action_deadline
                days_waiting = (today - deadline).days
            except Exception:
                days_waiting = 0

        result.append(WaitingTooLongItem(
            project_id=str(activity.project_id),
            project_name=activity.project.project_name,
            next_action=activity.next_action or "等待客户反馈",
            days_waiting=max(days_waiting, 0),
        ))

    result.sort(key=lambda x: x.days_waiting, reverse=True)
    return Response.success(data=result, message="获取成功")


@router.get("/intelligence-trends", response_model=Response[list[IntelligenceTrendItem]])
async def get_intelligence_trends(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """读取真实每日快照；没有历史时只返回已有日期，不补造趋势。"""
    days = min(max(days, 1), 365)
    since = date.today() - timedelta(days=days - 1)
    snapshots = db.query(ProjectIntelligenceSnapshot).filter(
        ProjectIntelligenceSnapshot.snapshot_date >= since
    ).order_by(ProjectIntelligenceSnapshot.snapshot_date.asc()).all()
    grouped: dict[date, list[ProjectIntelligenceSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.snapshot_date, []).append(snapshot)

    result = []
    for snapshot_date, items in grouped.items():
        project_count = len(items)
        result.append(IntelligenceTrendItem(
            snapshot_date=snapshot_date,
            project_count=project_count,
            covered_project_count=sum(1 for item in items if item.last_activity_at is not None),
            risk_project_count=sum(
                1 for item in items if item.health_status in ("风险", "严重风险")
            ),
            average_risk_score=round(
                sum(item.risk_score for item in items) / project_count, 1
            ) if project_count else 0,
            activity_count_7d=sum(item.activity_count_7d for item in items),
            active_warning_count=sum(item.active_warning_count for item in items),
        ))
    return Response.success(data=result, message="获取成功")


@router.get("/waiting-email-threads", response_model=Response[list[WaitingEmailThreadItem]])
async def get_waiting_email_threads(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    threshold = get_thresholds()["email_waiting_reply_days"]
    return Response.success(data=_waiting_email_threads(db, threshold)[:20], message="获取成功")


@router.get("/management-insights", response_model=Response[list[ManagementInsightItem]])
async def get_management_insights(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """生成有来源、有时间的管理建议，不把建议伪装成项目事实。"""
    now = datetime.now()
    insights: list[ManagementInsightItem] = []
    raw_count = db.query(func.count(DailyReportRawEntry.id)).scalar() or 0
    pending_count = db.query(func.count(DailyReportRawEntry.id)).filter(
        DailyReportRawEntry.analysis_status == "待人工匹配"
    ).scalar() or 0
    if pending_count:
        insights.append(ManagementInsightItem(
            insight_id="data-coverage",
            priority="high" if pending_count / max(raw_count, 1) > 0.5 else "medium",
            title="优先提升日报匹配覆盖率",
            reason=f"{raw_count} 条原始日报中仍有 {pending_count} 条未进入项目时间轴。",
            recommendation="先处理高置信度待匹配项目别名，再评估风险和项目活跃度。",
            evidence_source="日报原始数据中心",
            evidence_at=db.query(func.max(DailyReportRawEntry.updated_at)).scalar(),
        ))

    latest_activity = db.query(func.max(ActivityLog.occurred_at)).scalar()
    if latest_activity and (_days_since(latest_activity, now) or 0) > 7:
        insights.append(ManagementInsightItem(
            insight_id="data-freshness",
            priority="high",
            title="确认近期情报是否断流",
            reason=f"驾驶舱最新业务活动停留在 {latest_activity.strftime('%Y-%m-%d')}。",
            recommendation="检查今日日报源和邮箱同步，并确认海外项目是否转为邮件沟通。",
            evidence_source="项目活动日志",
            evidence_at=latest_activity,
        ))

    risk_projects = [
        project for project in _active_projects(db)
        if _health(project) in (HealthStatus.RISK, HealthStatus.SERIOUS_RISK)
    ]
    risk_projects.sort(
        key=lambda project: _days_since(project.last_activity_at or project.created_at, now) or 0,
        reverse=True,
    )
    for project in risk_projects[:4]:
        reason = _project_risk_reason(project, now)
        insights.append(ManagementInsightItem(
            insight_id=f"project-{project.id}",
            priority="high" if _health(project) == HealthStatus.SERIOUS_RISK else "medium",
            title=f"关注项目：{project.project_name}",
            reason=reason,
            recommendation="请负责人确认项目是否仍有效，并补充最新进展、下一步动作和预计时间。",
            project_id=project.id,
            evidence_source="项目活动时效规则",
            evidence_at=project.last_activity_at or project.created_at,
        ))

    waiting_threads = _waiting_email_threads(db, get_thresholds()["email_waiting_reply_days"])
    for item in waiting_threads[:2]:
        insights.append(ManagementInsightItem(
            insight_id=f"email-{item.email_id}",
            priority="medium",
            title=f"客户邮件待回复：{item.project_name}",
            reason=f"邮件《{item.subject}》发出后已等待 {item.waiting_days} 天。",
            recommendation="确认客户是否收到，并安排一次明确的跟进动作。",
            project_id=item.project_id,
            evidence_source="邮件线程",
            evidence_at=item.sent_at,
        ))
    priority_order = {"high": 3, "medium": 2, "low": 1}
    insights.sort(key=lambda item: priority_order.get(item.priority, 0), reverse=True)
    return Response.success(data=insights[:8], message="获取成功")
