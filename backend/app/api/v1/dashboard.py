"""
驾驶舱 API 路由

管理概览、阶段分布、风险项目、国家分布、渠道贡献等分析接口。
SQLite 兼容版本。
"""
from datetime import datetime, date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.project import Project
from app.models.channel import Channel
from app.models.activity_log import ActivityLog
from app.models.warning import WarningInstance
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
    TodayFollowupItem,
    WaitingTooLongItem,
)
from app.schemas.common import Response

router = APIRouter(tags=["驾驶舱"])


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

    # 基础统计
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    in_progress = db.query(func.count(Project.id)).filter(Project.status == "进行中").scalar() or 0
    risk_projects = db.query(func.count(Project.id)).filter(
        Project.health_status.in_(["风险", "严重风险"])
    ).scalar() or 0

    # 本月验收（SQLite 兼容：字符串比较）
    month_str = month_start.strftime("%Y-%m-%d")
    monthly_accepted = db.query(func.count(Project.id)).filter(
        Project.updated_at >= month_str
    ).scalar() or 0

    # 本月新增
    monthly_new = db.query(func.count(Project.id)).filter(
        Project.created_at >= month_str
    ).scalar() or 0

    # 僵尸项目（30天无活动）
    thirty_days_ago = now - timedelta(days=30)
    zombie_projects = db.query(func.count(Project.id)).filter(
        Project.last_activity_at < thirty_days_ago
    ).scalar() or 0

    fake_progress = 0  # MVP 阶段返回 0

    # 沉睡渠道（60天无活动）
    sixty_days_ago = (now - timedelta(days=60)).date()
    inactive_channels = db.query(func.count(Channel.id)).filter(
        Channel.last_contact_date < sixty_days_ago
    ).scalar() or 0

    summary = DashboardSummary(
        total_projects=total_projects,
        in_progress_projects=in_progress,
        risk_projects=risk_projects,
        monthly_acceptance_projects=monthly_accepted,
        monthly_new_projects=monthly_new,
        zombie_projects=zombie_projects,
        fake_progress_projects=fake_progress,
        inactive_channels=inactive_channels,
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

    total = db.query(func.count(Project.id)).scalar() or 1

    items = []
    for stage in ProjectStage:
        count = db.query(func.count(Project.id)).filter(
            Project.current_stage == stage.value
        ).scalar() or 0
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

    projects = db.query(Project).filter(
        Project.health_status.in_(["风险", "严重风险"]),
        Project.status == "进行中"
    ).limit(10).all()

    result = []
    for project in projects:
        days_stuck = 0
        if project.stage_entered_at:
            days_stuck = (now - project.stage_entered_at).days

        result.append(RiskProjectItem(
            project_id=str(project.id),
            project_name=project.project_name,
            current_stage=project.current_stage,
            blocker=project.risk_level or "未知",
            days_stuck=days_stuck,
            owner_name=project.owner.full_name if project.owner else None,
            risk_level=project.risk_level or "低",
        ))

    result.sort(key=lambda x: x.days_stuck, reverse=True)
    return Response.success(data=result, message="获取成功")


# ============ 国家分布接口 ============
@router.get("/country-distribution", response_model=Response[list[CountryDistributionItem]])
async def get_country_distribution(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取国家分布统计"""
    country_stats = db.query(
        Project.country,
        func.count(Project.id).label("project_count"),
        func.sum(Project.project_amount).label("total_amount"),
    ).group_by(Project.country).all()

    result = []
    for country, project_count, total_amount in country_stats:
        risk_count = db.query(func.count(Project.id)).filter(
            Project.country == country,
            Project.health_status.in_(["风险", "严重风险"])
        ).scalar() or 0

        result.append(CountryDistributionItem(
            country=country or "未知",
            project_count=project_count,
            total_amount=float(total_amount or 0),
            risk_count=risk_count,
        ))

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
            Project.status == "已验收"
        ).scalar() or 0

        result.append(ChannelContributionItem(
            channel_id=str(channel.id),
            channel_name=channel.channel_name,
            project_count=project_count,
            total_amount=float(total_amount or 0),
            bid_win_rate=float(channel.bid_win_rate or 0),
            poc_success_rate=0.0,
        ))

    return Response.success(data=result, message="获取成功")


# ============ 健康度分布接口 ============
@router.get("/health-distribution", response_model=Response[list[HealthDistributionItem]])
async def get_health_distribution(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目健康度分布"""
    from app.models.enums import HealthStatus

    total = db.query(func.count(Project.id)).scalar() or 1

    items = []
    for health in HealthStatus:
        count = db.query(func.count(Project.id)).filter(
            Project.health_status == health.value
        ).scalar() or 0
        percentage = round(count / total * 100, 2)
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
    today_str = today.strftime("%Y-%m-%d")

    # 查询已超过计划验收日期且状态为进行中的项目
    projects = db.query(Project).filter(
        Project.planned_acceptance.isnot(None),
        Project.planned_acceptance < today_str,
        Project.status != "已验收",
        Project.status != "已关闭",
    ).limit(20).all()

    result = []
    for project in projects:
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
    ninety_days_ago = today - timedelta(days=90)

    # 查询失联超过90天的渠道
    # 使用日期类型比较，避免字符串比较问题
    channels = db.query(Channel).filter(
        (Channel.last_contact_date.is_(None)) | (Channel.last_contact_date < ninety_days_ago)
    ).limit(20).all()

    result = []
    for channel in channels:
        # 计算失联天数
        days_since_last_contact = 0
        
        # 如果有最后联系日期，直接计算
        if channel.last_contact_date:
            try:
                last_contact_date = channel.last_contact_date
                if isinstance(last_contact_date, datetime):
                    last_contact_date = last_contact_date.date()
                days_since_last_contact = (today - last_contact_date).days
            except Exception as e:
                days_since_last_contact = 0
        
        # 如果从未联系过或计算结果为0，使用创建日期计算
        if days_since_last_contact <= 0 and not channel.last_contact_date:
            if channel.created_at:
                try:
                    created_date = channel.created_at.date() if hasattr(channel.created_at, 'date') else today
                    days_since_last_contact = (today - created_date).days
                except Exception:
                    days_since_last_contact = 90  # 默认90天

        # 确保天数为正数
        days_since_last_contact = max(days_since_last_contact, 0)

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
            last_contact_date=channel.last_contact_date,
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
    seen_projects = set()
    for activity in activities:
        if not activity.project_id or str(activity.project_id) in seen_projects:
            continue

        project = activity.project
        if not project or project.status == "已验收" or project.status == "已关闭":
            continue

        seen_projects.add(str(activity.project_id))

        # 根据 risk_level 决定优先级
        priority = "low"
        if project.risk_level == "严重风险" or project.risk_level == "高":
            priority = "high"
        elif project.risk_level == "中" or project.health_status == "风险":
            priority = "medium"

        result.append(TodayFollowupItem(
            project_id=str(project.id),
            project_name=project.project_name,
            next_action=activity.next_action,
            priority=priority,
            owner_name=project.owner.full_name if project.owner else None,
        ))

        if len(result) >= 10:
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
    today_str = today.strftime("%Y-%m-%d")

    # 查询有下一步动作截止日期且已超期的活动
    activities = db.query(ActivityLog).filter(
        ActivityLog.next_action_deadline.isnot(None),
        ActivityLog.next_action_deadline < today_str,
    ).order_by(ActivityLog.next_action_deadline).limit(20).all()

    result = []
    for activity in activities:
        if not activity.project:
            continue

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
