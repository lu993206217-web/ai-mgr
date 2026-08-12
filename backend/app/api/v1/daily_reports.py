"""
项目活动日报同步 API。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.db.session import get_db
from app.models.daily_report import (
    DailyReportBinding as DailyReportBindingModel,
    DailyReportSyncRun as DailyReportSyncRunModel,
    DailyReportUnmatchedProject as DailyReportUnmatchedProjectModel,
    DailyReportRawEntry as DailyReportRawEntryModel,
)
from app.models.user import User as UserModel
from app.schemas.common import PaginatedResponse, Response
from app.schemas.daily_report import (
    BindUnmatchedRequest,
    DailyReportBinding,
    DailyReportSyncRequest,
    DailyReportSyncRun,
    DailyReportUnmatchedProject,
    DailyReportRawEntry,
)
from app.services.daily_report_sync import DailyReportSyncService

router = APIRouter(tags=["项目活动日报"])


def run_daily_report_sync_task(
    run_id: UUID,
    month: Optional[str],
    lookback_days: Optional[int],
    start_date: Any,
    end_date: Any,
    project_ids: Optional[list[UUID]],
    trigger_ingestion: bool,
) -> None:
    """在请求返回后继续执行日报同步，避免前端长时间等待。"""
    db = SessionLocal()
    try:
        service = DailyReportSyncService(db)
        service.execute_sync_run(
            run_id=run_id,
            month=month,
            lookback_days=lookback_days,
            start_date=start_date,
            end_date=end_date,
            project_ids=project_ids,
            trigger_ingestion=trigger_ingestion,
        )
    finally:
        db.close()


@router.post("/sync", response_model=Response[DailyReportSyncRun])
async def sync_daily_reports(
    sync_data: DailyReportSyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """手动触发项目活动日报同步，后台执行。"""
    service = DailyReportSyncService(db)
    run = service.create_sync_run(
        month=sync_data.month or datetime.now().strftime("%Y-%m"),
        lookback_days=sync_data.lookback_days,
        start_date=sync_data.start_date,
        end_date=sync_data.end_date,
        trigger_type="manual",
        created_by=current_user.id,
    )
    background_tasks.add_task(
        run_daily_report_sync_task,
        run.id,
        sync_data.month or datetime.now().strftime("%Y-%m"),
        sync_data.lookback_days,
        sync_data.start_date,
        sync_data.end_date,
        sync_data.project_ids,
        sync_data.trigger_ingestion,
    )
    return Response.success(data=run, message="同步任务已提交，后端正在执行")


@router.get("/runs", response_model=Response[PaginatedResponse[DailyReportSyncRun]])
async def get_sync_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取日报同步运行记录。"""
    query = db.query(DailyReportSyncRunModel)
    total = query.count()
    items = (
        query.order_by(DailyReportSyncRunModel.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/raw-entries", response_model=Response[PaginatedResponse[DailyReportRawEntry]])
async def get_raw_entries(
    analysis_status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """查看先落库、后分析的日报原始条目。"""
    query = db.query(DailyReportRawEntryModel)
    if analysis_status:
        query = query.filter(DailyReportRawEntryModel.analysis_status == analysis_status)
    if start_date:
        query = query.filter(DailyReportRawEntryModel.source_date >= start_date)
    if end_date:
        query = query.filter(DailyReportRawEntryModel.source_date <= end_date)
    total = query.count()
    rows = (
        query.order_by(DailyReportRawEntryModel.source_date.desc(), DailyReportRawEntryModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        item = DailyReportRawEntry.model_validate(row)
        item.ai_project_name = row.project.project_name if row.project else None
        items.append(item)
    return Response.success(
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/unmatched", response_model=Response[PaginatedResponse[DailyReportUnmatchedProject]])
async def get_unmatched_projects(
    month: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    confidence_level: Optional[str] = Query(None, pattern="^(high|low)$"),
    keyword: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取未匹配日报项目队列。"""
    query = db.query(DailyReportUnmatchedProjectModel)
    if month:
        query = query.filter(DailyReportUnmatchedProjectModel.month == month)
    if status_filter:
        query = query.filter(DailyReportUnmatchedProjectModel.status == status_filter)
    if confidence_level == "high":
        query = query.filter(DailyReportUnmatchedProjectModel.suggested_score >= 0.8)
    elif confidence_level == "low":
        query = query.filter(DailyReportUnmatchedProjectModel.suggested_score < 0.8)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        raw_match_exists = (
            db.query(DailyReportRawEntryModel.id)
            .filter(
                DailyReportRawEntryModel.project_key == DailyReportUnmatchedProjectModel.project_key,
                func.strftime("%Y-%m", DailyReportRawEntryModel.source_date)
                == DailyReportUnmatchedProjectModel.month,
                or_(
                    DailyReportRawEntryModel.external_project_name.ilike(pattern),
                    DailyReportRawEntryModel.creator_name.ilike(pattern),
                    DailyReportRawEntryModel.original_summary.ilike(pattern),
                    DailyReportRawEntryModel.ai_reason.ilike(pattern),
                ),
            )
            .exists()
        )
        query = query.filter(
            or_(
                DailyReportUnmatchedProjectModel.external_project_name.ilike(pattern),
                DailyReportUnmatchedProjectModel.project_key.ilike(pattern),
                DailyReportUnmatchedProjectModel.suggested_project_name.ilike(pattern),
                raw_match_exists,
            )
        )
    total = query.count()
    rows = (
        query.order_by(
            DailyReportUnmatchedProjectModel.suggested_score.desc(),
            DailyReportUnmatchedProjectModel.updated_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        raw_query = (
            db.query(DailyReportRawEntryModel)
            .filter(
                DailyReportRawEntryModel.project_key == row.project_key,
                func.strftime("%Y-%m", DailyReportRawEntryModel.source_date) == row.month,
            )
        )
        matched_raw = None
        if keyword and keyword.strip():
            pattern = f"%{keyword.strip()}%"
            matched_raw = raw_query.filter(
                or_(
                    DailyReportRawEntryModel.external_project_name.ilike(pattern),
                    DailyReportRawEntryModel.creator_name.ilike(pattern),
                    DailyReportRawEntryModel.original_summary.ilike(pattern),
                    DailyReportRawEntryModel.ai_reason.ilike(pattern),
                )
            ).order_by(
                DailyReportRawEntryModel.source_date.desc(), DailyReportRawEntryModel.created_at.desc()
            ).first()
        latest_raw = matched_raw or raw_query.order_by(
            DailyReportRawEntryModel.source_date.desc(), DailyReportRawEntryModel.created_at.desc()
        ).first()
        source_names = [
            value[0]
            for value in raw_query.with_entities(DailyReportRawEntryModel.external_project_name)
            .distinct()
            .order_by(DailyReportRawEntryModel.external_project_name.asc())
            .all()
            if value[0]
        ]
        item = DailyReportUnmatchedProject.model_validate(row)
        if latest_raw:
            item.sample_original_summary = latest_raw.original_summary
            item.sample_ai_reason = latest_raw.ai_reason
            item.sample_creator_name = latest_raw.creator_name
            item.sample_source_date = latest_raw.source_date
        item.source_project_names = source_names
        if len(source_names) > 1:
            item.diagnosis_hint = f"数据源疑似混用：同一 project_key 出现 {len(source_names)} 个项目名称"
        elif not row.suggested_project_id:
            item.diagnosis_hint = "本地项目库没有可靠候选，请核对是否缺少项目或名称不一致"
        else:
            item.diagnosis_hint = "存在候选但置信度不足，请人工核对匹配关系"
        items.append(item)
    return Response.success(
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.post("/unmatched/{unmatched_id}/bind", response_model=Response[DailyReportUnmatchedProject])
async def bind_unmatched_project(
    unmatched_id: UUID,
    bind_data: BindUnmatchedRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """人工确认未匹配日报项目与本地项目的绑定。"""
    service = DailyReportSyncService(db)
    try:
        record = service.bind_unmatched(
            unmatched_id=unmatched_id,
            project_id=bind_data.project_id,
            user_id=current_user.id,
            sync_after_bind=bind_data.sync_after_bind,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    imported_count = int(getattr(record, "imported_activity_count", 0))
    message = f"绑定成功，已导入 {imported_count} 条活动" if bind_data.sync_after_bind else "绑定成功"
    return Response.success(data=record, message=message)


@router.post("/unmatched/{unmatched_id}/ignore", response_model=Response[DailyReportUnmatchedProject])
async def ignore_unmatched_project(
    unmatched_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """忽略未匹配日报项目。"""
    service = DailyReportSyncService(db)
    try:
        record = service.ignore_unmatched(unmatched_id=unmatched_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response.success(data=record, message="已忽略")


@router.get("/bindings", response_model=Response[PaginatedResponse[DailyReportBinding]])
async def get_bindings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取日报项目绑定列表。"""
    query = db.query(DailyReportBindingModel)
    total = query.count()
    rows = (
        query.order_by(DailyReportBindingModel.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        item = DailyReportBinding.model_validate(row)
        item.project_name = row.project.project_name if row.project else None
        items.append(item)

    return Response.success(
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/projects/{project_id}/binding", response_model=Response[Optional[DailyReportBinding]])
async def get_project_binding(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取指定项目的日报绑定。"""
    row = (
        db.query(DailyReportBindingModel)
        .filter(DailyReportBindingModel.project_id == project_id, DailyReportBindingModel.is_active.is_(True))
        .first()
    )
    if not row:
        return Response.success(data=None, message="未绑定")
    item = DailyReportBinding.model_validate(row)
    item.project_name = row.project.project_name if row.project else None
    return Response.success(data=item, message="获取成功")
