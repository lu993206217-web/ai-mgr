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


@router.post("/check", response_model=Response)
async def trigger_warning_check(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """手动触发预警检查"""
    now = datetime.now()
    rules = db.query(WarningRuleModel).filter(WarningRuleModel.is_active == True).all()

    total_instances = 0
    for rule in rules:
        recent_instance = db.query(WarningInstanceModel).filter(
            WarningInstanceModel.rule_id == rule.id,
            WarningInstanceModel.created_at >= now - timedelta(days=rule.cooldown_days)
        ).first()

        if recent_instance:
            continue

        check_fn = {
            "R001": _check_r001, "R002": _check_r002, "R003": _check_r003,
            "R004": _check_r004, "R005": _check_r005, "R006": _check_r006, "R007": _check_r007,
        }.get(rule.rule_code)

        if check_fn:
            instances = check_fn(db, rule, now)
            db.add_all(instances)
            total_instances += len(instances)

    db.commit()

    return Response.success(data={"instances_created": total_instances}, message=f"预警检查完成，生成 {total_instances} 个预警实例")


def _check_r001(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R001: 无跟进预警"""
    seven_days_ago = now - timedelta(days=7)
    projects = db.query(ProjectModel).filter(
        ProjectModel.status == "进行中",
        or_(ProjectModel.last_activity_at == None, ProjectModel.last_activity_at < seven_days_ago)
    ).all()

    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(
            WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃"
        ).first()
        if not existing:
            days = (now - project.last_activity_at).days if project.last_activity_at else 999
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」已{days}天无活动"))
    return instances


def _check_r002(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R002: 验收超时预警"""
    thirty_days_ago = now - timedelta(days=30)
    projects = db.query(ProjectModel).filter(ProjectModel.status == "进行中", ProjectModel.current_stage == "验收", ProjectModel.stage_entered_at < thirty_days_ago).all()
    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now - project.stage_entered_at).days if project.stage_entered_at else 0
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」在验收阶段已停留{days}天"))
    return instances


def _check_r003(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R003: POC超时预警"""
    sixty_days_ago = now - timedelta(days=60)
    projects = db.query(ProjectModel).filter(ProjectModel.status == "进行中", ProjectModel.current_stage == "POC", ProjectModel.stage_entered_at < sixty_days_ago).all()
    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now - project.stage_entered_at).days if project.stage_entered_at else 0
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」在POC阶段已停留{days}天"))
    return instances


def _check_r004(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R004: 报价后无进展预警"""
    ninety_days_ago = now - timedelta(days=90)
    quotes = db.query(QuoteModel).filter(QuoteModel.quote_date < ninety_days_ago, QuoteModel.project_id == None).all()
    instances = []
    for quote in quotes:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.message.like(f"%{quote.id}%")).first()
        if not existing:
            days = (now - quote.quote_date).days
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=None, severity=rule.severity, status="活跃", message=f"报价「{quote.product_name}」({quote.quote_amount} {quote.currency}) 已{days}天未形成项目"))
    return instances


def _check_r005(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R005: 渠道沉没预警"""
    sixty_days_ago = (now - timedelta(days=60)).date()
    channels = db.query(ChannelModel).filter(ChannelModel.cooperation_status == "活跃", or_(ChannelModel.last_contact_date == None, ChannelModel.last_contact_date < sixty_days_ago)).all()
    instances = []
    for channel in channels:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.channel_id == channel.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now.date() - channel.last_contact_date).days if channel.last_contact_date else 999
            instances.append(WarningInstanceModel(rule_id=rule.id, channel_id=channel.id, severity=rule.severity, status="活跃", message=f"渠道「{channel.channel_name}」已{days}天无活动"))
    return instances


def _check_r006(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R006: 假性推进预警"""
    projects = db.query(ProjectModel).filter(ProjectModel.status == "进行中").all()
    instances = []
    for project in projects:
        recent_activities = db.query(ActivityLogModel).filter(ActivityLogModel.project_id == project.id).order_by(ActivityLogModel.occurred_at.desc()).limit(3).all()
        if len(recent_activities) < 3:
            continue
        if all(a.next_action == "等待客户反馈" for a in recent_activities):
            existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
            if not existing:
                instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」连续3次活动为等待客户反馈，疑似假性推进"))
    return instances


def _check_r007(db: Session, rule: WarningRuleModel, now: datetime) -> list:
    """R007: 项目长期未验收预警"""
    one_eighty_days_ago = now - timedelta(days=180)
    projects = db.query(ProjectModel).filter(ProjectModel.status == "进行中", ProjectModel.planned_acceptance != None, ProjectModel.planned_acceptance < one_eighty_days_ago).all()
    instances = []
    for project in projects:
        existing = db.query(WarningInstanceModel).filter(WarningInstanceModel.rule_id == rule.id, WarningInstanceModel.project_id == project.id, WarningInstanceModel.status == "活跃").first()
        if not existing:
            days = (now - project.planned_acceptance).days if project.planned_acceptance else 0
            instances.append(WarningInstanceModel(rule_id=rule.id, project_id=project.id, severity=rule.severity, status="活跃", message=f"项目「{project.project_name}」计划验收时间已过期{days}天，仍未验收"))
    return instances
