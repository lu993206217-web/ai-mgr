"""项目状态事件、情报快照与管理层趋势服务。"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.enums import HealthStatus, ProjectStatus, WarningStatus
from app.models.project import Project
from app.models.project_intelligence import ProjectIntelligenceSnapshot, ProjectStateEvent
from app.models.warning import WarningInstance


def _text(value: Any) -> str:
    return str(getattr(value, "value", value))


def record_state_event(
    db: Session,
    project: Project,
    event_type: str,
    from_value: Any,
    to_value: Any,
    changed_by: Optional[UUID],
    note: Optional[str] = None,
    source: str = "manual",
    occurred_at: Optional[datetime] = None,
) -> ProjectStateEvent:
    event = ProjectStateEvent(
        project_id=project.id,
        event_type=event_type,
        from_value=_text(from_value) if from_value is not None else None,
        to_value=_text(to_value),
        note=(note or "").strip() or None,
        source=source,
        occurred_at=occurred_at or datetime.now(),
        changed_by=changed_by,
    )
    db.add(event)
    return event


def ensure_baseline_events(db: Session) -> int:
    """为历史项目补一条可辨识的基线，不伪造过去的阶段流转。"""
    created = 0
    for project in db.query(Project).all():
        existing_types = {
            event_type
            for (event_type,) in db.query(ProjectStateEvent.event_type)
            .filter(ProjectStateEvent.project_id == project.id)
            .all()
        }
        if "stage_baseline" not in existing_types and "stage_change" not in existing_types:
            record_state_event(
                db, project, "stage_baseline", None, project.current_stage, project.created_by,
                note="P2启用时按当前阶段建立基线，非历史流转记录",
                source="baseline_backfill", occurred_at=datetime.now(),
            )
            created += 1
        if "status_baseline" not in existing_types and "status_change" not in existing_types:
            record_state_event(
                db, project, "status_baseline", None, project.status, project.created_by,
                note="P2启用时按当前状态建立基线，非历史流转记录",
                source="baseline_backfill", occurred_at=datetime.now(),
            )
            created += 1
    return created


def _health_at(
    project: Project,
    target_date: date,
    last_activity_at: Optional[datetime],
    has_blocker: bool,
) -> HealthStatus:
    reference = last_activity_at or project.created_at
    days = max((target_date - reference.date()).days, 0)
    if not last_activity_at:
        return HealthStatus.HEALTHY if days <= 7 else HealthStatus.SERIOUS_RISK
    if days <= 7:
        return HealthStatus.ATTENTION if has_blocker else HealthStatus.HEALTHY
    if days <= 14:
        return HealthStatus.RISK if has_blocker else HealthStatus.ATTENTION
    if days <= 30:
        return HealthStatus.SERIOUS_RISK if has_blocker else HealthStatus.RISK
    return HealthStatus.SERIOUS_RISK


def build_daily_snapshots(db: Session, snapshot_date: Optional[date] = None) -> dict[str, int]:
    """生成或刷新指定日期的项目快照。仅使用该日期之前已经发生的事实。"""
    snapshot_date = snapshot_date or date.today()
    day_end = datetime.combine(snapshot_date, time.max)
    seven_days_ago = day_end - timedelta(days=7)
    thirty_days_ago = day_end - timedelta(days=30)
    created = 0
    updated = 0

    ensure_baseline_events(db)
    for project in db.query(Project).filter(Project.created_at <= day_end).all():
        activities = (
            db.query(ActivityLog)
            .filter(ActivityLog.project_id == project.id, ActivityLog.occurred_at <= day_end)
            .order_by(ActivityLog.occurred_at.desc())
            .all()
        )
        latest = activities[0] if activities else None
        last_activity_at = latest.occurred_at if latest else None
        inactivity_days = max((snapshot_date - (last_activity_at or project.created_at).date()).days, 0)
        has_blocker = any(activity.blocker_flag for activity in activities[:3])
        health = _health_at(project, snapshot_date, last_activity_at, has_blocker)
        activity_count_7d = sum(1 for activity in activities if activity.occurred_at >= seven_days_ago)
        activity_count_30d = sum(1 for activity in activities if activity.occurred_at >= thirty_days_ago)
        active_warning_count = db.query(WarningInstance).filter(
            WarningInstance.project_id == project.id,
            WarningInstance.status == WarningStatus.ACTIVE,
            WarningInstance.created_at <= day_end,
        ).count()
        overdue_action_count = sum(
            1 for activity in activities
            if activity.next_action_deadline and activity.next_action_deadline < snapshot_date
        )
        source_counts = Counter(
            _text(activity.source) for activity in activities if activity.occurred_at >= thirty_days_ago
        )
        base_score = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.ATTENTION: 25,
            HealthStatus.RISK: 60,
            HealthStatus.SERIOUS_RISK: 90,
        }[health]
        risk_score = min(100, base_score + min(active_warning_count * 3, 9) + min(overdue_action_count * 2, 6))

        snapshot = db.query(ProjectIntelligenceSnapshot).filter(
            ProjectIntelligenceSnapshot.project_id == project.id,
            ProjectIntelligenceSnapshot.snapshot_date == snapshot_date,
        ).first()
        payload = {
            "project_status": _text(project.status),
            "project_stage": _text(project.current_stage),
            "health_status": health.value,
            "risk_score": risk_score,
            "last_activity_at": last_activity_at,
            "inactivity_days": inactivity_days,
            "activity_count_7d": activity_count_7d,
            "activity_count_30d": activity_count_30d,
            "active_warning_count": active_warning_count,
            "overdue_action_count": overdue_action_count,
            "source_counts_json": json.dumps(source_counts, ensure_ascii=False),
            "generated_at": datetime.now(),
        }
        if snapshot:
            for key, value in payload.items():
                setattr(snapshot, key, value)
            updated += 1
        else:
            db.add(ProjectIntelligenceSnapshot(
                project_id=project.id,
                snapshot_date=snapshot_date,
                **payload,
            ))
            created += 1

    db.commit()
    return {"created": created, "updated": updated}
