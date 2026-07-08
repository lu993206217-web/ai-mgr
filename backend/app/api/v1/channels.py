from uuid import UUID
"""
渠道管理 API 路由
"""
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.channel import Channel as ChannelModel
from app.schemas.channel import (
    Channel as ChannelSchema,
    ChannelCreate,
    ChannelUpdate,
)
from app.schemas.common import Response, PaginatedResponse

router = APIRouter(tags=["渠道管理"])


@router.get("", response_model=Response[PaginatedResponse[ChannelSchema]])
async def get_channels(
    country: Optional[str] = Query(None),
    cooperation_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取渠道列表"""
    query = db.query(ChannelModel)

    if country:
        query = query.filter(ChannelModel.country == country)
    if cooperation_status:
        query = query.filter(ChannelModel.cooperation_status == cooperation_status)

    total = query.count()
    offset = (page - 1) * page_size
    channels = query.order_by(ChannelModel.created_at.desc()).offset(offset).limit(page_size).all()

    channel_list = []
    for ch in channels:
        ch_dict = ChannelSchema.model_validate(ch)
        ch_dict.total_projects = len(ch.projects) if ch.projects else 0
        ch_dict.total_amount = sum([p.project_amount for p in ch.projects if p.project_amount]) if ch.projects else 0
        channel_list.append(ch_dict)

    return Response.success(
        data=PaginatedResponse.create(items=channel_list, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/{channel_id}", response_model=Response[ChannelSchema])
async def get_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取渠道详情"""
    channel = db.query(ChannelModel).filter(ChannelModel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="渠道不存在")

    ch_dict = ChannelSchema.model_validate(channel)
    ch_dict.total_projects = len(channel.projects) if channel.projects else 0
    ch_dict.total_amount = sum([p.project_amount for p in channel.projects if p.project_amount]) if channel.projects else 0

    return Response.success(data=ch_dict, message="获取成功")


@router.post("", response_model=Response[ChannelSchema])
async def create_channel(
    channel_data: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建新渠道"""
    existing = db.query(ChannelModel).filter(ChannelModel.channel_name == channel_data.channel_name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="渠道名称已存在")

    channel = ChannelModel(
        **channel_data.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return Response.success(data=ChannelSchema.model_validate(channel), message="创建成功")


@router.put("/{channel_id}", response_model=Response[ChannelSchema])
async def update_channel(
    channel_id: UUID,
    channel_data: ChannelUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新渠道信息"""
    channel = db.query(ChannelModel).filter(ChannelModel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="渠道不存在")

    update_data = channel_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    channel.updated_by = current_user.id
    channel.updated_at = datetime.now()

    db.commit()
    db.refresh(channel)

    return Response.success(data=ChannelSchema.model_validate(channel), message="更新成功")


@router.delete("/{channel_id}", response_model=Response)
async def delete_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除渠道"""
    channel = db.query(ChannelModel).filter(ChannelModel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="渠道不存在")

    # 检查是否有关联的有效项目（排除已归档项目）
    from app.models.project import Project as ProjectModel
    related_projects = db.query(ProjectModel.project_name).filter(
        ProjectModel.channel_id == channel_id,
        ProjectModel.status != "已归档"
    ).all()
    
    if related_projects:
        # 提取项目名称列表
        project_names = [project.project_name for project in related_projects]
        project_list = "、".join(project_names)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"渠道下有关联项目，无法删除。关联项目：{project_list}"
        )

    db.delete(channel)
    db.commit()

    return Response.success(message="删除成功")
