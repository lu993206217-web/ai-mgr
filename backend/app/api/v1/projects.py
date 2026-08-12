"""
项目管理 API 路由

项目 CRUD + 阶段流转。
"""
from uuid import UUID
from datetime import datetime, date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.activity_log import ActivityLog as ActivityLogModel
from app.models.project_file import ProjectFile as ProjectFileModel
from app.models.project_intelligence import ProjectStateEvent as ProjectStateEventModel
from app.services.project_intelligence import record_state_event
from app.services.activity_presentation import enrich_activity_presentation
from app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectQueryParams,
    StageTransitionRequest,
    ProjectStateEventItem,
    ActivityLog,
    ActivityLogCreate,
    ProjectFile,
    ProjectFileCreate,
    ProjectFileUpdate,
)
from app.schemas.common import Response, PaginatedResponse

router = APIRouter(tags=["项目管理"])


# ============ 项目列表接口 ============
@router.get("", response_model=Response[PaginatedResponse[Project]])
async def get_projects(
    query_params: ProjectQueryParams = Depends(),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    获取项目列表

    支持多条件筛选、分页、排序。
    """
    query = db.query(ProjectModel)

    if query_params.project_name:
        query = query.filter(ProjectModel.project_name.ilike(f"%{query_params.project_name}%"))
    if query_params.country:
        query = query.filter(ProjectModel.country == query_params.country)
    if query_params.customer_id:
        query = query.filter(ProjectModel.customer_id == query_params.customer_id)
    if query_params.channel_id:
        query = query.filter(ProjectModel.channel_id == query_params.channel_id)
    if query_params.owner_id:
        query = query.filter(ProjectModel.owner_id == query_params.owner_id)
    if query_params.current_stage:
        query = query.filter(ProjectModel.current_stage == query_params.current_stage)
    if query_params.health_status:
        query = query.filter(ProjectModel.health_status == query_params.health_status)
    if query_params.risk_level:
        query = query.filter(ProjectModel.risk_level == query_params.risk_level)
    
    # 默认过滤已归档项目，除非明确指定状态
    if query_params.status:
        query = query.filter(ProjectModel.status == query_params.status)
    else:
        query = query.filter(ProjectModel.status != "已归档")
        
    if query_params.created_after:
        query = query.filter(ProjectModel.created_at >= query_params.created_after)
    if query_params.created_before:
        query = query.filter(ProjectModel.created_at <= query_params.created_before)

    total = query.count()

    offset_val = (query_params.page - 1) * query_params.page_size
    order_column = getattr(ProjectModel, query_params.order_by, ProjectModel.created_at)
    if query_params.order_dir == "desc":
        order_column = order_column.desc()
    query = query.order_by(order_column)

    projects = query.offset(offset_val).limit(query_params.page_size).all()

    project_list = []
    for project in projects:
        project_dict = Project.model_validate(project)
        project_dict.owner_name = project.owner.full_name if project.owner else None
        project_dict.customer_name = project.customer.customer_name if project.customer else None
        project_dict.channel_name = project.channel.channel_name if project.channel else None

        if project.last_activity_at:
            days_since = (datetime.now() - project.last_activity_at).days
            project_dict.days_since_last_activity = days_since

        project_dict.activity_count = len(project.activities)
        
        # 使用计算的健康度，考虑阻塞状态（处理可能的异常）
        try:
            project_dict.health_status = project.health_status_computed
        except Exception as e:
            # 如果计算健康度失败（例如活动日志为空或其他异常），使用数据库中的值
            project_dict.health_status = project.health_status

        project_list.append(project_dict)

    return Response.success(
        data=PaginatedResponse.create(
            items=project_list,
            total=total,
            page=query_params.page,
            page_size=query_params.page_size,
        ),
        message="获取成功",
    )


# ============ 项目详情接口 ============
@router.get("/{project_id}", response_model=Response[Project])
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目详情"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    project_dict = Project.model_validate(project)
    project_dict.owner_name = project.owner.full_name if project.owner else None
    project_dict.customer_name = project.customer.customer_name if project.customer else None
    project_dict.channel_name = project.channel.channel_name if project.channel else None

    if project.last_activity_at:
        project_dict.days_since_last_activity = (datetime.now() - project.last_activity_at).days

    project_dict.activity_count = len(project.activities)
    
    # 使用计算的健康度，考虑阻塞状态（处理可能的异常）
    try:
        project_dict.health_status = project.health_status_computed
    except Exception as e:
        # 如果计算健康度失败（例如活动日志为空或其他异常），使用数据库中的值
        project_dict.health_status = project.health_status

    return Response.success(data=project_dict, message="获取成功")


# ============ 创建项目接口 ============
@router.post("", response_model=Response[Project])
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建新项目"""
    # 如果未指定负责人，默认为当前用户
    create_data = project_data.model_dump(exclude_unset=True)

    # 处理undefined或空字符串的情况
    if not create_data.get("owner_id") or create_data.get("owner_id") == "":
        create_data["owner_id"] = current_user.id

    # customer_id可选：处理空字符串转为None
    if create_data.get("customer_id") == "":
        create_data["customer_id"] = None

    # 确保currency有默认值
    if not create_data.get("currency"):
        create_data["currency"] = "USD"

    project = ProjectModel(
        **create_data,
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    db.add(project)
    db.flush()
    record_state_event(
        db, project, "stage_baseline", None, project.current_stage, current_user.id,
        note="项目创建时阶段", source="project_create", occurred_at=project.created_at or datetime.now(),
    )
    record_state_event(
        db, project, "status_baseline", None, project.status, current_user.id,
        note="项目创建时状态", source="project_create", occurred_at=project.created_at or datetime.now(),
    )
    db.commit()
    db.refresh(project)

    return Response.success(data=Project.model_validate(project), message="创建成功")


# ============ 更新项目接口 ============
@router.put("/{project_id}", response_model=Response[Project])
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新项目信息"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    old_stage = project.current_stage
    old_status = project.status
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    if "current_stage" in update_data and project.current_stage != old_stage:
        project.stage_entered_at = datetime.now()
        record_state_event(
            db, project, "stage_change", old_stage, project.current_stage, current_user.id,
            note="通过项目编辑修改阶段", source="project_update",
        )
    if "status" in update_data and project.status != old_status:
        record_state_event(
            db, project, "status_change", old_status, project.status, current_user.id,
            note="通过项目编辑修改状态", source="project_update",
        )

    project.updated_by = current_user.id
    project.updated_at = datetime.now()

    db.commit()
    db.refresh(project)

    return Response.success(data=Project.model_validate(project), message="更新成功")


# ============ 阶段流转接口 ============
@router.post("/{project_id}/stage", response_model=Response[Project])
async def transition_stage(
    project_id: UUID,
    transition_data: StageTransitionRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """项目阶段流转"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    old_stage = project.current_stage
    if str(getattr(old_stage, "value", old_stage)) == transition_data.target_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目标阶段与当前阶段相同，无需流转",
        )
    project.current_stage = transition_data.target_stage
    project.stage_entered_at = datetime.now()
    project.updated_by = current_user.id
    project.updated_at = datetime.now()
    record_state_event(
        db, project, "stage_change", old_stage, project.current_stage, current_user.id,
        note=transition_data.transition_note, source="stage_transition",
    )

    db.commit()
    db.refresh(project)

    return Response.success(data=Project.model_validate(project), message="阶段流转成功")


@router.get("/{project_id}/state-events", response_model=Response[list[ProjectStateEventItem]])
async def get_project_state_events(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目阶段与状态的不可覆盖历史。"""
    if not db.query(ProjectModel.id).filter(ProjectModel.id == project_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    events = db.query(ProjectStateEventModel).filter(
        ProjectStateEventModel.project_id == project_id
    ).order_by(ProjectStateEventModel.occurred_at.desc()).all()
    return Response.success(data=events, message="获取成功")


# ============ 删除项目接口 ============
@router.delete("/{project_id}", response_model=Response)
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除项目（真实删除，从数据库中移除）"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    # 真实删除项目
    db.delete(project)
    db.commit()

    return Response.success(message="删除成功")


# ============ 项目活动日志接口 ============
@router.get("/{project_id}/activities", response_model=Response[PaginatedResponse[ActivityLog]])
async def get_project_activities(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    activity_type: Optional[str] = Query(None, description="活动类型筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目活动日志列表"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    query = db.query(ActivityLogModel).filter(ActivityLogModel.project_id == project_id)
    
    # 活动类型筛选
    if activity_type:
        query = query.filter(ActivityLogModel.activity_type == activity_type)
    
    # 日期范围筛选
    if start_date:
        query = query.filter(ActivityLogModel.occurred_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(ActivityLogModel.occurred_at <= datetime.combine(end_date, datetime.max.time()))
    
    total = query.count()
    
    offset_val = (page - 1) * page_size
    activities = query.order_by(ActivityLogModel.occurred_at.desc()).offset(offset_val).limit(page_size).all()
    
    activity_list = []
    for activity in activities:
        activity_dict = ActivityLog.model_validate(activity)
        activity_dict.owner_name = activity.owner.full_name if activity.owner else None
        enrich_activity_presentation(db, activity, activity_dict)
        activity_list.append(activity_dict)
    
    return Response.success(
        data=PaginatedResponse.create(
            items=activity_list,
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="获取成功",
    )


@router.post("/{project_id}/activities", response_model=Response[ActivityLog])
async def create_project_activity(
    project_id: UUID,
    activity_data: ActivityLogCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建项目活动日志"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    create_data = activity_data.model_dump()
    activity = ActivityLogModel(
        **create_data,
        project_id=project_id,
        owner_id=current_user.id,
        source="MANUAL",
    )

    db.add(activity)
    db.flush()
    from app.services.workflow_center import ingest_activity_evidence

    ingest_activity_evidence(db, activity, confidence=1.0, reason="项目详情人工活动")
    db.commit()
    db.refresh(activity)

    # 更新项目的最后活动时间
    project.last_activity_at = activity.occurred_at
    project.updated_at = datetime.now()
    db.commit()

    activity_dict = ActivityLog.model_validate(activity)
    activity_dict.owner_name = activity.owner.full_name if activity.owner else None

    return Response.success(data=activity_dict, message="创建成功")


# ============ 项目文件接口 ============
@router.get("/{project_id}/files", response_model=Response[PaginatedResponse[ProjectFile]])
async def get_project_files(
    project_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    file_category: Optional[str] = Query(None, description="文件分类筛选"),
    keyword: Optional[str] = Query(None, description="文件名称关键字"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取项目文件列表"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    query = db.query(ProjectFileModel).filter(ProjectFileModel.project_id == project_id)
    if file_category:
        query = query.filter(ProjectFileModel.file_category == file_category)
    if keyword:
        query = query.filter(ProjectFileModel.file_name.ilike(f"%{keyword}%"))

    total = query.count()
    offset_val = (page - 1) * page_size
    files = query.order_by(ProjectFileModel.created_at.desc()).offset(offset_val).limit(page_size).all()

    file_list = []
    for item in files:
        file_dict = ProjectFile.model_validate(item)
        file_dict.created_by_name = item.creator.full_name if item.creator else None
        file_list.append(file_dict)

    return Response.success(
        data=PaginatedResponse.create(
            items=file_list,
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="获取成功",
    )


@router.post("/{project_id}/files", response_model=Response[ProjectFile])
async def create_project_file(
    project_id: UUID,
    file_data: ProjectFileCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建项目文件记录"""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    create_data = file_data.model_dump()
    project_file = ProjectFileModel(
        **create_data,
        project_id=project_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(project_file)
    db.commit()
    db.refresh(project_file)

    file_dict = ProjectFile.model_validate(project_file)
    file_dict.created_by_name = current_user.full_name

    return Response.success(data=file_dict, message="创建成功")


@router.put("/{project_id}/files/{file_id}", response_model=Response[ProjectFile])
async def update_project_file(
    project_id: UUID,
    file_id: UUID,
    file_data: ProjectFileUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新项目文件记录"""
    project_file = (
        db.query(ProjectFileModel)
        .filter(ProjectFileModel.project_id == project_id, ProjectFileModel.id == file_id)
        .first()
    )
    if not project_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目文件不存在")

    update_data = file_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project_file, field, value)

    project_file.updated_by = current_user.id
    project_file.updated_at = datetime.now()
    db.commit()
    db.refresh(project_file)

    file_dict = ProjectFile.model_validate(project_file)
    file_dict.created_by_name = project_file.creator.full_name if project_file.creator else None

    return Response.success(data=file_dict, message="更新成功")


@router.delete("/{project_id}/files/{file_id}", response_model=Response)
async def delete_project_file(
    project_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除项目文件记录"""
    project_file = (
        db.query(ProjectFileModel)
        .filter(ProjectFileModel.project_id == project_id, ProjectFileModel.id == file_id)
        .first()
    )
    if not project_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目文件不存在")

    db.delete(project_file)
    db.commit()

    return Response.success(message="删除成功")
