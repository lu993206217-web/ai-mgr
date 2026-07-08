"""
Activity Log API 路由
"""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.activity_log import ActivityLog as ActivityLogModel
from app.models.project import Project as ProjectModel
from app.schemas.activity_log import (
    ActivityLog,
    ActivityLogCreate,
    ActivityLogUpdate,
    ActivityLogQueryParams,
)
from app.schemas.common import Response, PaginatedResponse

router = APIRouter(tags=["活动日志"])


@router.get("", response_model=Response[PaginatedResponse[ActivityLog]])
async def get_activities(
    query_params: ActivityLogQueryParams = Depends(),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取活动日志列表"""
    query = db.query(ActivityLogModel)

    if query_params.project_id:
        query = query.filter(ActivityLogModel.project_id == query_params.project_id)
    if query_params.channel_id:
        query = query.filter(ActivityLogModel.channel_id == query_params.channel_id)
    if query_params.owner_id:
        query = query.filter(ActivityLogModel.owner_id == query_params.owner_id)
    if query_params.activity_type:
        query = query.filter(ActivityLogModel.activity_type == query_params.activity_type)
    if query_params.next_action:
        query = query.filter(ActivityLogModel.next_action == query_params.next_action)
    if query_params.blocker_flag is not None:
        query = query.filter(ActivityLogModel.blocker_flag == query_params.blocker_flag)
    if query_params.source:
        query = query.filter(ActivityLogModel.source == query_params.source)
    if query_params.occurred_after:
        query = query.filter(ActivityLogModel.occurred_at >= query_params.occurred_after)
    if query_params.occurred_before:
        query = query.filter(ActivityLogModel.occurred_at <= query_params.occurred_before)

    total = query.count()

    offset_val = (query_params.page - 1) * query_params.page_size
    order_column = getattr(ActivityLogModel, query_params.order_by, ActivityLogModel.occurred_at)
    if query_params.order_dir == "desc":
        order_column = order_column.desc()
    query = query.order_by(order_column)

    activities = query.offset(offset_val).limit(query_params.page_size).all()

    activity_list = []
    for act in activities:
        act_dict = ActivityLog.model_validate(act)
        act_dict.project_name = act.project.project_name if act.project else None
        act_dict.channel_name = act.channel.channel_name if act.channel else None
        act_dict.owner_name = act.owner.full_name if act.owner else None
        activity_list.append(act_dict)

    return Response.success(
        data=PaginatedResponse.create(items=activity_list, total=total, page=query_params.page, page_size=query_params.page_size),
        message="获取成功",
    )


@router.get("/{activity_id}", response_model=Response[ActivityLog])
async def get_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取活动日志详情"""
    activity = db.query(ActivityLogModel).filter(ActivityLogModel.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动日志不存在")

    act_dict = ActivityLog.model_validate(activity)
    act_dict.project_name = activity.project.project_name if activity.project else None
    act_dict.channel_name = activity.channel.channel_name if activity.channel else None
    act_dict.owner_name = activity.owner.full_name if activity.owner else None

    return Response.success(data=act_dict, message="获取成功")


@router.post("", response_model=Response[ActivityLog])
async def create_activity(
    activity_data: ActivityLogCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建活动日志"""
    activity = ActivityLogModel(**activity_data.model_dump())
    db.add(activity)

    if activity.project_id:
        project = db.query(ProjectModel).filter(ProjectModel.id == activity.project_id).first()
        if project:
            project.last_activity_at = activity.occurred_at
            project.updated_at = datetime.now()

    db.commit()
    db.refresh(activity)

    return Response.success(data=ActivityLog.model_validate(activity), message="创建成功")


@router.put("/{activity_id}", response_model=Response[ActivityLog])
async def update_activity(
    activity_id: UUID,
    activity_data: ActivityLogUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新活动日志信息"""
    activity = db.query(ActivityLogModel).filter(ActivityLogModel.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动日志不存在")

    update_data = activity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    activity.updated_at = datetime.now()
    db.commit()
    db.refresh(activity)

    return Response.success(data=ActivityLog.model_validate(activity), message="更新成功")


@router.delete("/{activity_id}", response_model=Response)
async def delete_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除活动日志"""
    activity = db.query(ActivityLogModel).filter(ActivityLogModel.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动日志不存在")

    db.delete(activity)
    db.commit()

    return Response.success(message="删除成功")
