"""
预警管理 API 路由
"""
from datetime import datetime, timedelta
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.warning import WarningRule as WarningRuleModel, WarningInstance as WarningInstanceModel
from app.models.project import Project as ProjectModel
from app.models.channel import Channel as ChannelModel
from app.models.activity_log import ActivityLog as ActivityLogModel
from app.models.quote import Quote as QuoteModel
from app.schemas.warning import (
    WarningRule,
    WarningRuleCreate,
    WarningRuleUpdate,
    WarningInstance,
    WarningInstanceHandle,
    WarningInstanceQueryParams,
)
from app.schemas.common import Response, PaginatedResponse
from app.api.v1.config import get_thresholds
from app.models.enums import NextAction, ProjectStage, ProjectStatus, WarningStatus

router = APIRouter(tags=["预警管理"])


@router.get("/rules", response_model=Response[PaginatedResponse[WarningRule]])
async def get_warning_rules(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取预警规则列表"""
    query = db.query(WarningRuleModel)
    total = query.count()
    rules = query.offset((page - 1) * page_size).limit(page_size).all()

    rule_list = []
    for rule in rules:
        rule_dict = WarningRule.model_validate(rule)
        rule_dict.instance_count = len(rule.instances) if rule.instances else 0
        rule_list.append(rule_dict)

    return Response.success(
        data=PaginatedResponse.create(items=rule_list, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.post("/rules", response_model=Response[WarningRule])
async def create_warning_rule(
    rule_data: WarningRuleCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建预警规则"""
    existing = db.query(WarningRuleModel).filter(WarningRuleModel.rule_code == rule_data.rule_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="规则代码已存在")

    rule = WarningRuleModel(
        **rule_data.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    return Response.success(data=rule, message="创建成功")


@router.put("/rules/{rule_id}", response_model=Response[WarningRule])
async def update_warning_rule(
    rule_id: UUID,
    rule_data: WarningRuleUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新预警规则"""
    rule = db.query(WarningRuleModel).filter(WarningRuleModel.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")

    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_by = current_user.id
    rule.updated_at = datetime.now()

    db.commit()
    db.refresh(rule)

    return Response.success(data=rule, message="更新成功")


@router.delete("/rules/{rule_id}", response_model=Response)
async def delete_warning_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除预警规则"""
    rule = db.query(WarningRuleModel).filter(WarningRuleModel.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")

    db.delete(rule)
    db.commit()

    return Response.success(message="删除成功")


@router.get("/instances", response_model=Response[PaginatedResponse[WarningInstance]])
async def get_warning_instances(
    query_params: WarningInstanceQueryParams = Depends(),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取预警实例列表"""
    query = db.query(WarningInstanceModel)

    if query_params.rule_id:
        query = query.filter(WarningInstanceModel.rule_id == query_params.rule_id)
    if query_params.project_id:
        query = query.filter(WarningInstanceModel.project_id == query_params.project_id)
    if query_params.channel_id:
        query = query.filter(WarningInstanceModel.channel_id == query_params.channel_id)
    if query_params.severity:
        query = query.filter(WarningInstanceModel.severity == query_params.severity)
    if query_params.status:
        query = query.filter(WarningInstanceModel.status == query_params.status)
    if query_params.created_after:
        query = query.filter(WarningInstanceModel.created_at >= query_params.created_after)
    if query_params.created_before:
        query = query.filter(WarningInstanceModel.created_at <= query_params.created_before)

    total = query.count()

    offset_val = (query_params.page - 1) * query_params.page_size
    order_column = getattr(WarningInstanceModel, query_params.order_by, WarningInstanceModel.created_at)
    if query_params.order_dir == "desc":
        order_column = order_column.desc()
    query = query.order_by(order_column)

    instances = query.offset(offset_val).limit(query_params.page_size).all()

    instance_list = []
    for inst in instances:
        inst_dict = WarningInstance.model_validate(inst)
        inst_dict.rule_name = inst.rule.rule_name if inst.rule else None
        inst_dict.project_name = inst.project.project_name if inst.project else None
        inst_dict.channel_name = inst.channel.channel_name if inst.channel else None
        instance_list.append(inst_dict)

    return Response.success(
        data=PaginatedResponse.create(items=instance_list, total=total, page=query_params.page, page_size=query_params.page_size),
        message="获取成功",
    )


@router.post("/instances/{instance_id}/handle", response_model=Response[WarningInstance])
async def handle_warning_instance(
    instance_id: UUID,
    handle_data: WarningInstanceHandle,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """处理预警实例"""
    instance = db.query(WarningInstanceModel).filter(WarningInstanceModel.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预警实例不存在")

    instance.status = handle_data.status
    instance.handled_by = current_user.id
    instance.handled_at = datetime.now()
    instance.handle_note = handle_data.handle_note

    db.commit()
    db.refresh(instance)

    return Response.success(data=instance, message="处理成功")


@router.post("/instances/{instance_id}/resolve", response_model=Response[WarningInstance])
async def resolve_warning_instance(
    instance_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """兼容页面快捷处理入口。"""
    instance = db.query(WarningInstanceModel).filter(WarningInstanceModel.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预警实例不存在")
    instance.status = WarningStatus.HANDLED
    instance.handled_by = current_user.id
    instance.handled_at = datetime.now()
    instance.handle_note = "人工标记已处理"
    db.commit()
    db.refresh(instance)
    return Response.success(data=instance, message="处理成功")


@router.post("/check", response_model=Response)
async def trigger_warning_check(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """手动触发预警检查"""
    total_instances = run_warning_check(db)
    return Response.success(data={"instances_created": total_instances}, message=f"预警检查完成，生成 {total_instances} 个预警实例")


def run_warning_check(db: Session) -> int:
    """执行一次预警检查，供手工接口和后台定时任务共用。"""
    now = datetime.now()
    rules = db.query(WarningRuleModel).filter(WarningRuleModel.is_active == True).all()

    _resolve_legacy_warnings_that_no_longer_apply(db, now)
    total_instances = 0
    for rule in rules:
        check_fn = {
            "R001": _check_r001, "R002": _check_r002, "R003": _check_r003,
            "R004": _check_r004, "R005": _check_r005, "R006": _check_r006, "R007": _check_r007,
        }.get(rule.rule_code)

        if check_fn:
            instances = check_fn(db, rule, now)
            db.add_all(instances)
            total_instances += len(instances)

    from app.services.workflow_center import evaluate_workflow_alerts

    workflow_result = evaluate_workflow_alerts(db, now)
    total_instances += workflow_result["created"]
    db.commit()
    return total_instances


def _resolve_legacy_warnings_that_no_longer_apply(db: Session, now: datetime) -> None:
    """阈值延长或项目有新进展后，自动解除已经不成立的旧预警。"""
    thresholds = get_thresholds()
    active_instances = db.query(WarningInstanceModel).filter(
        WarningInstanceModel.status == WarningStatus.ACTIVE
    ).all()
    for instance in active_instances:
        code = instance.rule.rule_code if instance.rule else ""
        project = instance.project
        applies = True
        if code == "R001" and project:
            reference = project.last_activity_at or project.created_at
            applies = project.status == ProjectStatus.IN_PROGRESS and (now - reference).days > thresholds["no_activity_warning_days"]
        elif code == "R002" and project:
            applies = (
                project.status == ProjectStatus.IN_PROGRESS
                and project.current_stage == ProjectStage.ACCEPTANCE
                and bool(project.stage_entered_at)
                and (now - project.stage_entered_at).days > thresholds["acceptance_overdue_days"]
            )
        elif code == "R003" and project:
            applies = (
                project.status == ProjectStatus.IN_PROGRESS
                and project.current_stage == ProjectStage.POC
                and bool(project.stage_entered_at)
                and (now - project.stage_entered_at).days > thresholds["poc_overdue_days"]
            )
        elif code == "R005" and instance.channel:
            from app.api.v1.dashboard import _effective_channel_contact

            applies = (now.date() - _effective_channel_contact(db, instance.channel)).days > thresholds["sunk_channel_warning_days"]
        elif code == "R006" and project:
            count = thresholds["fake_progress_count"]
            recent = db.query(ActivityLogModel).filter(
                ActivityLogModel.project_id == project.id
            ).order_by(ActivityLogModel.occurred_at.desc()).limit(count).all()
            applies = len(recent) == count and all(
                item.next_action == NextAction.WAITING_CUSTOMER for item in recent
            )
        elif code == "R007" and project:
            applies = (
                project.status == ProjectStatus.IN_PROGRESS
                and bool(project.planned_acceptance)
                and (now.date() - project.planned_acceptance).days > thresholds["acceptance_plan_overdue_days"]
            )
        if not applies:
            instance.status = WarningStatus.HANDLED
            instance.handled_at = now
            instance.handle_note = "系统根据新进展或延长后的阈值自动解除"


def _check_r001(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R001: 无跟进预警"""
    threshold = get_thresholds()["no_activity_warning_days"]
    cutoff = now - timedelta(days=threshold)
    projects = db.query(ProjectModel).filter(
        ProjectModel.status == ProjectStatus.IN_PROGRESS,
        or_(
            ProjectModel.last_activity_at < cutoff,
            and_(ProjectModel.last_activity_at == None, ProjectModel.created_at < cutoff),
        )
    ).all()

    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(
            WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃"
        ).first()
        if not existing:
            days = (now - (project.last_activity_at or project.created_at)).days
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」已{days}天无活动"))
    return instances


def _check_r002(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R002: 验收超时预警"""
    cutoff = now - timedelta(days=get_thresholds()["acceptance_overdue_days"])
    projects = db.query(ProjectModel).filter(ProjectModel.status == ProjectStatus.IN_PROGRESS, ProjectModel.current_stage == ProjectStage.ACCEPTANCE, ProjectModel.stage_entered_at < cutoff).all()
    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now - project.stage_entered_at).days if project.stage_entered_at else 0
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」在验收阶段已停留{days}天"))
    return instances


def _check_r003(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R003: POC超时预警"""
    cutoff = now - timedelta(days=get_thresholds()["poc_overdue_days"])
    projects = db.query(ProjectModel).filter(ProjectModel.status == ProjectStatus.IN_PROGRESS, ProjectModel.current_stage == ProjectStage.POC, ProjectModel.stage_entered_at < cutoff).all()
    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now - project.stage_entered_at).days if project.stage_entered_at else 0
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」在POC阶段已停留{days}天"))
    return instances


def _check_r004(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R004: 报价后无进展预警"""
    cutoff = now - timedelta(days=get_thresholds()["quote_no_progress_days"])
    quotes = db.query(QuoteModel).filter(QuoteModel.quote_date < cutoff, QuoteModel.project_id == None).all()
    instances = []
    for quote in quotes:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.message.like(f"%{quote.id}%")).first()
        if not existing:
            days = (now - quote.quote_date).days
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=None, severity=rule.severity, status="活跃", message=f"报价「{quote.product_name}」({quote.quote_amount} {quote.currency}) 已{days}天未形成项目"))
    return instances


def _check_r005(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R005: 渠道沉没预警"""
    from app.api.v1.dashboard import _effective_channel_contact
    threshold = get_thresholds()["sunk_channel_days"]
    channels = db.query(ChannelModel).all()
    instances = []
    for channel in channels:
        effective_contact = _effective_channel_contact(db, channel)
        days = (now.date() - effective_contact).days
        if days <= threshold:
            continue
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.channel_id == channel.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            instances.append(WarningInstanceModel(rule_id=rule.id, channel_id=channel.id, severity=rule.severity, status="活跃", message=f"渠道「{channel.channel_name}」已{days}天无活动"))
    return instances


def _check_r006(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R006: 假性推进预警"""
    count = get_thresholds()["fake_progress_count"]
    projects = db.query(ProjectModel).filter(ProjectModel.status == ProjectStatus.IN_PROGRESS).all()
    instances = []
    for project in projects:
        recent_activities = db.query(ActivityLogModel).filter(ActivityLogModel.project_id == project.id).order_by(ActivityLogModel.occurred_at.desc()).limit(count).all()
        if len(recent_activities) < count:
            continue
        if all(a.next_action == NextAction.WAITING_CUSTOMER for a in recent_activities):
            existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
            if not existing:
                instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」连续{count}次活动为等待客户反馈，疑似假性推进"))
    return instances


def _check_r007(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R007: 项目长期未验收预警"""
    cutoff = now.date() - timedelta(days=get_thresholds()["acceptance_plan_overdue_days"])
    projects = db.query(ProjectModel).filter(ProjectModel.status == ProjectStatus.IN_PROGRESS, ProjectModel.planned_acceptance != None, ProjectModel.planned_acceptance < cutoff).all()
    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now.date() - project.planned_acceptance).days if project.planned_acceptance else 0
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」计划验收时间已过期{days}天，仍未验收"))
    return instances
