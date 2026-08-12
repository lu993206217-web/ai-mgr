"""无人值守的数据采集、AI分析、流程推进和告警编排。"""
from __future__ import annotations

from datetime import datetime, timedelta
import threading
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.workflow import WorkflowAutomationRun, WorkflowAutomationTask


DEFAULT_TASKS = (
    {
        "task_code": "email_sync",
        "task_name": "企业邮箱自动推进",
        "description": "拉取收件箱和已发送邮件，使用DeepSeek分析、匹配项目并推进流程事项。",
        "enabled": True,
        "schedule_type": "interval",
        "interval_minutes": max(1, settings.DINGTALK_MAIL_SYNC_INTERVAL_MINUTES),
    },
    {
        "task_code": "daily_report_sync",
        "task_name": "项目日报自动推进",
        "description": "拉取最近日报，保留原始数据，AI分析可靠匹配后生成活动并推进流程事项。",
        "enabled": settings.DAILY_REPORT_SYNC_ENABLED,
        "schedule_type": "daily",
        "schedule_hour": settings.DAILY_REPORT_SYNC_HOUR,
        "schedule_minute": settings.DAILY_REPORT_SYNC_MINUTE,
        "lookback_days": settings.DAILY_REPORT_SYNC_LOOKBACK_DAYS,
    },
    {
        "task_code": "warning_evaluation",
        "task_name": "流程告警自动复核",
        "description": "根据最新邮件和日报证据重新计算提醒、告警和严重告警，并自动解除失效告警。",
        "enabled": settings.ENABLE_WARNING_NOTIFICATION,
        "schedule_type": "interval",
        "interval_minutes": 15,
    },
)


def seed_automation_tasks(db: Session) -> None:
    """首次启动写入默认任务；页面修改过的配置不会被覆盖。"""
    changed = False
    for payload in DEFAULT_TASKS:
        exists = (
            db.query(WorkflowAutomationTask)
            .filter(WorkflowAutomationTask.task_code == payload["task_code"])
            .first()
        )
        if not exists:
            db.add(WorkflowAutomationTask(**payload))
            changed = True
    if changed:
        db.commit()


def recover_interrupted_runs(db: Session) -> int:
    """服务重启后释放上个进程遗留的排队/运行记录。"""
    runs = db.query(WorkflowAutomationRun).filter(
        WorkflowAutomationRun.status.in_(("排队中", "运行中"))
    ).all()
    if not runs:
        return 0
    now = datetime.now()
    for run in runs:
        run.status = "失败"
        run.finished_at = now
        run.error_message = "服务重启导致本次执行中断，系统将自动重试"
        run.task.last_status = "失败"
        run.task.last_error = run.error_message
        run.task.last_finished_at = now
        run.task.last_scheduled_at = None
    db.commit()
    return len(runs)


def _plain_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value and value.tzinfo:
        return value.replace(tzinfo=None)
    return value


def task_is_due(task: WorkflowAutomationTask, now: Optional[datetime] = None) -> bool:
    now = _plain_datetime(now or datetime.now())
    if not task.enabled:
        return False
    last_scheduled = _plain_datetime(task.last_scheduled_at)
    if task.schedule_type == "interval":
        if not last_scheduled:
            return True
        return now >= last_scheduled + timedelta(minutes=max(1, task.interval_minutes or 1))
    if task.schedule_type == "daily":
        target = now.replace(
            hour=task.schedule_hour or 0,
            minute=task.schedule_minute or 0,
            second=0,
            microsecond=0,
        )
        return now >= target and (not last_scheduled or last_scheduled.date() < now.date())
    return False


def next_run_at(task: WorkflowAutomationTask, now: Optional[datetime] = None) -> Optional[datetime]:
    now = _plain_datetime(now or datetime.now())
    if not task.enabled:
        return None
    last_scheduled = _plain_datetime(task.last_scheduled_at)
    if task.schedule_type == "interval":
        return now if not last_scheduled else max(
            now, last_scheduled + timedelta(minutes=max(1, task.interval_minutes or 1))
        )
    target = now.replace(
        hour=task.schedule_hour or 0,
        minute=task.schedule_minute or 0,
        second=0,
        microsecond=0,
    )
    if target < now or (last_scheduled and last_scheduled.date() == now.date()):
        target += timedelta(days=1)
    return target


def queue_automation_run(
    db: Session,
    task: WorkflowAutomationTask,
    *,
    trigger_type: str,
    created_by: Optional[UUID] = None,
) -> tuple[WorkflowAutomationRun, bool]:
    """创建运行记录；仍在运行的同类任务不会重复排队。"""
    now = datetime.now()
    active = (
        db.query(WorkflowAutomationRun)
        .filter(
            WorkflowAutomationRun.task_id == task.id,
            WorkflowAutomationRun.status.in_(("排队中", "运行中")),
        )
        .order_by(WorkflowAutomationRun.created_at.desc())
        .first()
    )
    if active:
        reference = _plain_datetime(active.started_at or active.created_at)
        if reference and reference >= now - timedelta(hours=2):
            return active, False
        active.status = "失败"
        active.finished_at = now
        active.error_message = "上次任务超过2小时未结束，系统已自动释放"

    run = WorkflowAutomationRun(
        task_id=task.id,
        trigger_type=trigger_type,
        status="排队中",
        created_by=created_by,
    )
    db.add(run)
    task.last_status = "排队中"
    if trigger_type == "scheduled":
        task.last_scheduled_at = now
    task.updated_at = now
    db.commit()
    db.refresh(run)
    return run, True


def _run_email_sync(db: Session) -> dict[str, Any]:
    from app.services.dingtalk_mail import DingTalkMailService

    service = DingTalkMailService()
    if not service.enabled:
        return {"skipped": True, "reason": "企业邮箱同步尚未启用"}
    if not service.configured:
        return {"skipped": True, "reason": "企业邮箱账号或第三方安全密码未配置"}
    result = service.sync(
        db,
        max_messages=settings.DINGTALK_MAIL_SYNC_LIMIT,
        unseen_only=False,
    )
    from app.api.v1.warnings import run_warning_check

    result["new_alert_count"] = run_warning_check(db)
    return result


def _run_daily_report_sync(db: Session, task: WorkflowAutomationTask) -> dict[str, Any]:
    from app.services.daily_report_sync import DailyReportSyncService

    if not settings.DAILY_REPORT_API_KEY:
        return {"skipped": True, "reason": "日报接口API Key未配置"}
    service = DailyReportSyncService(db)
    run = service.sync_month(
        lookback_days=task.lookback_days or settings.DAILY_REPORT_SYNC_LOOKBACK_DAYS,
        trigger_type="scheduled",
        trigger_ingestion=True,
    )
    result = {
        "sync_run_id": str(run.id),
        "month": run.month,
        "status": run.status,
        "imported_activity_count": run.imported_activity_count,
        "unmatched_count": run.unmatched_count,
        "skipped_duplicate_count": run.skipped_duplicate_count,
        "partial_error": run.error_message,
    }
    if run.status == "失败":
        raise RuntimeError(run.error_message or "日报同步失败")
    from app.api.v1.warnings import run_warning_check

    result["new_alert_count"] = run_warning_check(db)
    return result


def _run_warning_evaluation(db: Session) -> dict[str, Any]:
    from app.api.v1.warnings import run_warning_check

    return {"new_alert_count": run_warning_check(db)}


def _result_summary(task_code: str, result: dict[str, Any]) -> str:
    if result.get("skipped"):
        return f"已跳过：{result.get('reason', '数据源未就绪')}"
    if task_code == "email_sync":
        return (
            f"新增{result.get('imported_count', 0)}封，匹配{result.get('matched_count', 0)}封，"
            f"生成活动{result.get('activity_count', 0)}条，失败{result.get('failed_count', 0)}封"
        )
    if task_code == "daily_report_sync":
        return (
            f"导入活动{result.get('imported_activity_count', 0)}条，"
            f"未匹配{result.get('unmatched_count', 0)}条，重复跳过{result.get('skipped_duplicate_count', 0)}条"
        )
    return f"新增告警{result.get('new_alert_count', 0)}条"


def execute_automation_run(run_id: UUID) -> None:
    """在独立数据库会话中执行任务，供调度器和API后台任务共用。"""
    db = SessionLocal()
    try:
        run = db.query(WorkflowAutomationRun).filter(WorkflowAutomationRun.id == run_id).first()
        if not run:
            return
        task = run.task
        now = datetime.now()
        run.status = "运行中"
        run.started_at = now
        task.last_started_at = now
        task.last_status = "运行中"
        task.last_error = None
        db.commit()

        if task.task_code == "email_sync":
            result = _run_email_sync(db)
        elif task.task_code == "daily_report_sync":
            result = _run_daily_report_sync(db, task)
        elif task.task_code == "warning_evaluation":
            result = _run_warning_evaluation(db)
        else:
            raise RuntimeError(f"不支持的自动任务：{task.task_code}")

        finished = datetime.now()
        status = "已跳过" if result.get("skipped") else (
            "部分成功" if result.get("failed_count") or result.get("partial_error") else "成功"
        )
        run.status = status
        run.result_json = result
        run.finished_at = finished
        task.last_status = status
        task.last_result = _result_summary(task.task_code, result)
        task.last_error = result.get("partial_error")
        task.last_finished_at = finished
        task.updated_at = finished
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.query(WorkflowAutomationRun).filter(WorkflowAutomationRun.id == run_id).first()
        if run:
            finished = datetime.now()
            run.status = "失败"
            run.error_message = str(exc)[:2000]
            run.finished_at = finished
            run.task.last_status = "失败"
            run.task.last_error = str(exc)[:2000]
            run.task.last_finished_at = finished
            run.task.updated_at = finished
            db.commit()
    finally:
        db.close()


def dispatch_due_automation_tasks() -> None:
    """每分钟扫描到期任务；任务本身具备防重和运行留痕。"""
    db = SessionLocal()
    run_ids: list[UUID] = []
    try:
        seed_automation_tasks(db)
        now = datetime.now()
        for task in db.query(WorkflowAutomationTask).filter(WorkflowAutomationTask.enabled.is_(True)).all():
            if task_is_due(task, now):
                run, created = queue_automation_run(db, task, trigger_type="scheduled")
                if created:
                    run_ids.append(run.id)
    finally:
        db.close()
    # 各数据源独立运行，单个邮箱或外部接口变慢时不会阻塞日报与告警。
    for run_id in run_ids:
        threading.Thread(target=execute_automation_run, args=(run_id,), daemon=True).start()
