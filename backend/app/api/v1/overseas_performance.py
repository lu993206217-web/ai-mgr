"""海外管理绩效汇报 API。"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.overseas_performance import OverseasPerformanceReport
from app.models.user import User as UserModel
from app.schemas.common import Response
from app.schemas.overseas_performance import (
    GeneratePerformanceReportRequest,
    PerformanceConfigUpdate,
    PerformanceConfigView,
    PerformanceReportDetail,
    PerformanceReportList,
    PerformanceReportListItem,
)
from app.services.overseas_performance import (
    config_view,
    generate_report,
    get_or_create_config,
    report_view,
    save_config,
)


router = APIRouter(tags=["海外绩效汇报"])


@router.get("/config", response_model=Response[PerformanceConfigView])
async def get_performance_config(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    config = get_or_create_config(db, current_user.id)
    return Response.success(data=PerformanceConfigView(**config_view(config)), message="获取成功")


@router.put("/config", response_model=Response[PerformanceConfigView])
async def update_performance_config(
    body: PerformanceConfigUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    config = save_config(db, current_user.id, body.model_dump(exclude={"last_run_at"}))
    return Response.success(data=PerformanceConfigView(**config_view(config)), message="汇报配置已保存")


@router.post("/generate", response_model=Response[PerformanceReportDetail])
async def generate_performance_report(
    body: GeneratePerformanceReportRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    try:
        report = generate_report(
            db,
            user_id=current_user.id,
            start_date=body.start_date,
            end_date=body.end_date,
            period_label=body.period_label,
            period_type=body.period_type,
            scope=body.scope,
            trigger_type="manual",
        )
        db.commit()
        db.refresh(report)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"汇报生成失败：{str(exc)}",
        ) from exc
    return Response.success(data=PerformanceReportDetail(**report_view(report)), message="汇报已生成")


@router.get("/reports", response_model=Response[PerformanceReportList])
async def list_performance_reports(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    query = db.query(OverseasPerformanceReport).filter(OverseasPerformanceReport.user_id == current_user.id)
    total = query.count()
    reports = query.order_by(OverseasPerformanceReport.generated_at.desc()).limit(limit).all()
    items = [
        PerformanceReportListItem(**{
            "id": item.id,
            "period_label": item.period_label,
            "period_type": item.period_type,
            "start_date": item.start_date,
            "end_date": item.end_date,
            "scope": item.scope,
            "trigger_type": item.trigger_type,
            "status": item.status,
            "generated_at": item.generated_at,
        }) for item in reports
    ]
    return Response.success(data=PerformanceReportList(items=items, total=total), message="获取成功")


@router.get("/reports/{report_id}", response_model=Response[PerformanceReportDetail])
async def get_performance_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    report = db.query(OverseasPerformanceReport).filter(
        OverseasPerformanceReport.id == report_id,
        OverseasPerformanceReport.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="汇报记录不存在")
    return Response.success(data=PerformanceReportDetail(**report_view(report)), message="获取成功")
