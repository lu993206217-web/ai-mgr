"""流程中心 API。"""
from datetime import date, datetime, time
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.core.config import settings
from app.models.workflow import (
    WorkflowAlert, WorkflowAutomationRun, WorkflowAutomationTask,
    WorkflowItem, WorkflowStateEvent,
)
from app.schemas.common import PaginatedResponse, Response
from app.schemas.workflow import (
    WorkflowAlertHandleRequest,
    WorkflowAlertView,
    WorkflowAutomationRunView,
    WorkflowAutomationTaskUpdate,
    WorkflowAutomationTaskView,
    WorkflowAssignRequest,
    WorkflowItemCreate,
    WorkflowItemDetail,
    WorkflowItemView,
    WorkflowSummary,
    WorkflowTransitionRequest,
)
from app.services.workflow_center import (
    CLOSED_STATUSES,
    OPEN_STATUSES,
    VALID_STATUSES,
    evaluate_workflow_alerts,
    transition_item,
)
from app.services.workflow_automation import (
    execute_automation_run,
    next_run_at,
    queue_automation_run,
    seed_automation_tasks,
)
from app.services.mail_runtime_config import get_dingtalk_mail_config


router = APIRouter(tags=["流程中心"])
MANAGER_ROLES = {"管理员", "项目经理"}


def _scope_items(query, current_user: User):
    if current_user.role in MANAGER_ROLES:
        return query
    return query.filter(WorkflowItem.owner_id == current_user.id)


def _require_manager(current_user: User) -> None:
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员或项目经理可管理自动任务")


def _automation_task_view(task: WorkflowAutomationTask) -> WorkflowAutomationTaskView:
    source_ready = True
    source_message = "数据源已就绪"
    if task.task_code == "email_sync":
        config = get_dingtalk_mail_config()
        source_ready = config.enabled and config.configured
        source_message = "企业邮箱已配置" if source_ready else "请先启用企业邮箱并配置第三方安全密码"
    elif task.task_code == "daily_report_sync":
        source_ready = bool(settings.DAILY_REPORT_API_KEY)
        source_message = "日报接口已配置" if source_ready else "日报接口API Key未配置"
    return WorkflowAutomationTaskView(
        id=task.id,
        task_code=task.task_code,
        task_name=task.task_name,
        description=task.description,
        enabled=task.enabled,
        schedule_type=task.schedule_type,
        interval_minutes=task.interval_minutes,
        schedule_hour=task.schedule_hour,
        schedule_minute=task.schedule_minute,
        lookback_days=task.lookback_days,
        source_ready=source_ready,
        source_message=source_message,
        next_run_at=next_run_at(task),
        last_started_at=task.last_started_at,
        last_finished_at=task.last_finished_at,
        last_status=task.last_status,
        last_result=task.last_result,
        last_error=task.last_error,
    )


def _item_view(item: WorkflowItem, detail: bool = False):
    active_levels = [alert.level for alert in item.alerts if alert.status == "活跃"]
    level_order = {"提醒": 1, "告警": 2, "严重": 3}
    alert_level = max(active_levels, key=lambda value: level_order.get(value, 0), default=None)
    payload = {
        "id": item.id,
        "project_id": item.project_id,
        "project_name": item.project.project_name if item.project else None,
        "owner_id": item.owner_id,
        "owner_name": item.owner.full_name if item.owner else None,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "responsibility_party": item.responsibility_party,
        "priority": item.priority,
        "due_date": item.due_date,
        "source_type": item.source_type,
        "ai_generated": item.ai_generated,
        "ai_confidence": item.ai_confidence,
        "ai_reason": item.ai_reason,
        "last_progress_at": item.last_progress_at,
        "completed_at": item.completed_at,
        "evidence_count": len(item.evidences),
        "alert_level": alert_level,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
    if detail:
        payload["evidences"] = sorted(item.evidences, key=lambda value: value.evidence_at, reverse=True)
        payload["state_events"] = sorted(item.state_events, key=lambda value: value.occurred_at, reverse=True)
        return WorkflowItemDetail(**payload)
    return WorkflowItemView(**payload)


@router.get("/summary", response_model=Response[WorkflowSummary])
def get_workflow_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    today = date.today()
    base = _scope_items(db.query(WorkflowItem), current_user)
    total_open = base.filter(WorkflowItem.status.in_(OPEN_STATUSES)).count()
    mine_pending = db.query(WorkflowItem).filter(
        WorkflowItem.owner_id == current_user.id,
        WorkflowItem.status.in_(OPEN_STATUSES),
    ).count()
    return Response.success(data=WorkflowSummary(
        total_open=total_open,
        ai_pending=base.filter(WorkflowItem.status == "AI待确认").count(),
        mine_pending=mine_pending,
        waiting_external=base.filter(WorkflowItem.status == "等待外部").count(),
        due_today=base.filter(
            WorkflowItem.status.in_(OPEN_STATUSES), WorkflowItem.due_date == today
        ).count(),
        overdue=base.filter(
            WorkflowItem.status.in_(OPEN_STATUSES), WorkflowItem.due_date < today
        ).count(),
        suspected_complete=base.filter(WorkflowItem.status == "疑似完成").count(),
        active_alerts=db.query(WorkflowAlert).filter(WorkflowAlert.status == "活跃").count(),
    ))


@router.get("/automation/tasks", response_model=Response[list[WorkflowAutomationTaskView]])
def list_automation_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    seed_automation_tasks(db)
    tasks = db.query(WorkflowAutomationTask).order_by(WorkflowAutomationTask.created_at).all()
    return Response.success(data=[_automation_task_view(task) for task in tasks])


@router.put("/automation/tasks/{task_id}", response_model=Response[WorkflowAutomationTaskView])
def update_automation_task(
    task_id: UUID,
    payload: WorkflowAutomationTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_manager(current_user)
    task = db.query(WorkflowAutomationTask).filter(WorkflowAutomationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="自动任务不存在")
    if payload.schedule_type == "interval" and not payload.interval_minutes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="间隔任务必须填写执行间隔")
    if payload.schedule_type == "daily" and (
        payload.schedule_hour is None or payload.schedule_minute is None
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="每日任务必须填写执行时间")
    task.enabled = payload.enabled
    task.schedule_type = payload.schedule_type
    task.interval_minutes = payload.interval_minutes if payload.schedule_type == "interval" else None
    task.schedule_hour = payload.schedule_hour if payload.schedule_type == "daily" else None
    task.schedule_minute = payload.schedule_minute if payload.schedule_type == "daily" else None
    if task.task_code == "daily_report_sync":
        task.lookback_days = payload.lookback_days or task.lookback_days or 3
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)
    return Response.success(data=_automation_task_view(task), message="自动任务配置已保存")


@router.post("/automation/tasks/{task_id}/run", response_model=Response[WorkflowAutomationRunView])
def run_automation_task_now(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_manager(current_user)
    task = db.query(WorkflowAutomationTask).filter(WorkflowAutomationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="自动任务不存在")
    run, created = queue_automation_run(
        db, task, trigger_type="manual", created_by=current_user.id
    )
    if created:
        background_tasks.add_task(execute_automation_run, run.id)
    return Response.success(
        data=WorkflowAutomationRunView(
            id=run.id,
            task_id=run.task_id,
            task_name=task.task_name,
            trigger_type=run.trigger_type,
            status=run.status,
            result_json=run.result_json,
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
        ),
        message="任务已提交" if created else "该任务正在执行，本次未重复提交",
    )


@router.get("/automation/runs", response_model=Response[PaginatedResponse[WorkflowAutomationRunView]])
def list_automation_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = db.query(WorkflowAutomationRun)
    if task_id:
        query = query.filter(WorkflowAutomationRun.task_id == task_id)
    total = query.count()
    runs = (
        query.order_by(WorkflowAutomationRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    views = [WorkflowAutomationRunView(
        id=run.id,
        task_id=run.task_id,
        task_name=run.task.task_name if run.task else None,
        trigger_type=run.trigger_type,
        status=run.status,
        result_json=run.result_json,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    ) for run in runs]
    return Response.success(data=PaginatedResponse.create(
        items=views, total=total, page=page, page_size=page_size
    ))


@router.get("/items", response_model=Response[PaginatedResponse[WorkflowItemView]])
def list_workflow_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_value: Optional[str] = Query(None, alias="status"),
    responsibility_party: Optional[str] = None,
    project_id: Optional[UUID] = None,
    owner_id: Optional[UUID] = None,
    keyword: Optional[str] = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = _scope_items(db.query(WorkflowItem), current_user)
    if status_value:
        query = query.filter(WorkflowItem.status == status_value)
    if responsibility_party:
        query = query.filter(WorkflowItem.responsibility_party == responsibility_party)
    if project_id:
        query = query.filter(WorkflowItem.project_id == project_id)
    if owner_id:
        query = query.filter(WorkflowItem.owner_id == owner_id)
    if mine:
        query = query.filter(WorkflowItem.owner_id == current_user.id)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(or_(WorkflowItem.title.ilike(like), WorkflowItem.description.ilike(like)))
    total = query.count()
    items = (
        query.order_by(WorkflowItem.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(data=PaginatedResponse.create(
        items=[_item_view(item) for item in items], total=total, page=page, page_size=page_size
    ))


@router.post("/items", response_model=Response[WorkflowItemView])
def create_workflow_item(
    payload: WorkflowItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    owner_id = payload.owner_id or project.owner_id
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="负责人不存在")
    item = WorkflowItem(
        project_id=project.id,
        owner_id=owner.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        topic_key=f"manual:{project.id}:{datetime.now().timestamp()}",
        status="待接收",
        responsibility_party=payload.responsibility_party,
        priority=payload.priority,
        due_date=payload.due_date,
        source_type="手工录入",
        ai_generated=False,
        ai_confidence=1.0,
        ai_reason="人工创建",
        last_progress_at=datetime.now(),
    )
    db.add(item)
    db.flush()
    db.add(WorkflowStateEvent(
        workflow_item_id=item.id,
        from_status=None,
        to_status="待接收",
        source="manual",
        reason="人工创建事项",
        confidence=1.0,
        changed_by=current_user.id,
        occurred_at=datetime.now(),
    ))
    db.commit()
    db.refresh(item)
    return Response.success(data=_item_view(item), message="事项已创建")


@router.get("/items/{item_id}", response_model=Response[WorkflowItemDetail])
def get_workflow_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = _scope_items(db.query(WorkflowItem), current_user)
    item = query.filter(WorkflowItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事项不存在")
    return Response.success(data=_item_view(item, detail=True))


@router.post("/items/{item_id}/transition", response_model=Response[WorkflowItemView])
def transition_workflow_item(
    item_id: UUID,
    payload: WorkflowTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的事项状态")
    query = _scope_items(db.query(WorkflowItem), current_user)
    item = query.filter(WorkflowItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事项不存在")
    transition_item(db, item, payload.status, changed_by=current_user.id, note=payload.note)
    evaluate_workflow_alerts(db)
    db.commit()
    db.refresh(item)
    return Response.success(data=_item_view(item), message="事项状态已更新")


@router.post("/items/{item_id}/assign", response_model=Response[WorkflowItemView])
def assign_workflow_item(
    item_id: UUID,
    payload: WorkflowAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    item = db.query(WorkflowItem).filter(WorkflowItem.id == item_id).first()
    owner = db.query(User).filter(User.id == payload.owner_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事项不存在")
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="负责人不存在")
    if current_user.role not in MANAGER_ROLES and item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权转交该事项")
    item.owner_id = owner.id
    item.updated_at = datetime.now()
    db.add(WorkflowStateEvent(
        workflow_item_id=item.id,
        from_status=item.status,
        to_status=item.status,
        source="manual",
        reason=f"事项转交给{owner.full_name}",
        confidence=1.0,
        changed_by=current_user.id,
        occurred_at=datetime.now(),
    ))
    db.commit()
    db.refresh(item)
    return Response.success(data=_item_view(item), message="事项已转交")


@router.post("/alerts/evaluate", response_model=Response[dict])
def evaluate_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    result = evaluate_workflow_alerts(db)
    db.commit()
    return Response.success(data=result, message="流程告警已重新计算")


@router.get("/alerts", response_model=Response[PaginatedResponse[WorkflowAlertView]])
def list_workflow_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_value: Optional[str] = Query(None, alias="status"),
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = db.query(WorkflowAlert)
    if current_user.role not in MANAGER_ROLES:
        query = query.join(WorkflowItem, WorkflowAlert.workflow_item_id == WorkflowItem.id).filter(
            WorkflowItem.owner_id == current_user.id
        )
    if status_value:
        query = query.filter(WorkflowAlert.status == status_value)
    if level:
        query = query.filter(WorkflowAlert.level == level)
    total = query.count()
    alerts = (
        query.order_by(WorkflowAlert.last_evaluated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    views = [WorkflowAlertView(
        id=alert.id,
        workflow_item_id=alert.workflow_item_id,
        project_id=alert.project_id,
        project_name=alert.project.project_name if alert.project else None,
        item_title=alert.workflow_item.title if alert.workflow_item else None,
        alert_type=alert.alert_type,
        level=alert.level,
        status=alert.status,
        threshold_days=alert.threshold_days,
        elapsed_days=alert.elapsed_days,
        message=alert.message,
        evidence_at=alert.evidence_at,
        first_triggered_at=alert.first_triggered_at,
        last_evaluated_at=alert.last_evaluated_at,
        resolved_at=alert.resolved_at,
    ) for alert in alerts]
    return Response.success(data=PaginatedResponse.create(
        items=views, total=total, page=page, page_size=page_size
    ))


@router.post("/alerts/{alert_id}/handle", response_model=Response[WorkflowAlertView])
def handle_workflow_alert(
    alert_id: UUID,
    payload: WorkflowAlertHandleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    alert = db.query(WorkflowAlert).filter(WorkflowAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程告警不存在")
    alert.status = payload.status
    alert.resolved_at = datetime.now()
    alert.handled_by = current_user.id
    alert.handle_note = payload.note
    alert.last_evaluated_at = datetime.now()
    db.commit()
    db.refresh(alert)
    return Response.success(data=WorkflowAlertView(
        id=alert.id,
        workflow_item_id=alert.workflow_item_id,
        project_id=alert.project_id,
        project_name=alert.project.project_name if alert.project else None,
        item_title=alert.workflow_item.title if alert.workflow_item else None,
        alert_type=alert.alert_type,
        level=alert.level,
        status=alert.status,
        threshold_days=alert.threshold_days,
        elapsed_days=alert.elapsed_days,
        message=alert.message,
        evidence_at=alert.evidence_at,
        first_triggered_at=alert.first_triggered_at,
        last_evaluated_at=alert.last_evaluated_at,
        resolved_at=alert.resolved_at,
    ), message="流程告警已处理")
