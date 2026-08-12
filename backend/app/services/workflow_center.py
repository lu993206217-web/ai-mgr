"""流程事项生成、证据推进和分级告警。"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.config import get_thresholds
from app.models.activity_log import ActivityLog
from app.models.email_intelligence import EmailMessage
from app.models.project import Project
from app.models.workflow import WorkflowAlert, WorkflowEvidence, WorkflowItem, WorkflowStateEvent


OPEN_STATUSES = {"AI待确认", "待接收", "处理中", "等待外部", "疑似完成"}
CLOSED_STATUSES = {"已完成", "已取消"}
VALID_STATUSES = OPEN_STATUSES | CLOSED_STATUSES
COMPLETION_TERMS = (
    "已完成", "已经完成", "完成测试", "测试通过", "问题已解决", "已经解决",
    "处理完成", "已交付", "已经交付", "已验收", "验收通过", "closed", "resolved",
)
NEGATIVE_COMPLETION_TERMS = ("未完成", "尚未完成", "没有完成", "待完成", "未解决", "尚未解决")


def _plain(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip()


def _normalize_topic(value: str) -> str:
    value = re.sub(r"^((re|fw|fwd|回复|转发)\s*[:：]\s*)+", "", value.strip(), flags=re.I)
    value = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", value.casefold())
    return value[:160]


def _short(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _topic_key(activity: ActivityLog, email: Optional[EmailMessage], title: str) -> str:
    if email:
        # 部分企业邮箱会为同一往来链生成不同 Thread/Header，主题在同一项目内更稳定。
        # 项目ID + 归一化主题既能合并回复/转发，也不会跨项目串单。
        raw = f"email-topic:{activity.project_id}:{_normalize_topic(email.subject)}"
    else:
        raw = f"activity:{activity.project_id}:{_normalize_topic(title)[:80]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def consolidate_email_workflow_items(db: Session) -> dict[str, int]:
    """归并历史上因邮件Thread不稳定产生的同项目、同主题重复事项。"""
    items = (
        db.query(WorkflowItem)
        .filter(WorkflowItem.source_type == "邮件")
        .order_by(WorkflowItem.last_progress_at.desc())
        .all()
    )
    groups: dict[tuple[UUID, str], list[WorkflowItem]] = {}
    for item in items:
        normalized = _normalize_topic(item.title)
        if normalized:
            groups.setdefault((item.project_id, normalized), []).append(item)

    merged_items = moved_evidences = 0
    for (project_id, normalized), group in groups.items():
        primary = group[0]
        target_key = hashlib.sha256(
            f"email-topic:{project_id}:{normalized}".encode("utf-8")
        ).hexdigest()
        primary.topic_key = target_key
        if len(group) == 1:
            continue

        # 告警属于可重新计算的分析数据；归并后清除旧事项告警并统一重算。
        group_ids = [item.id for item in group]
        db.query(WorkflowAlert).filter(WorkflowAlert.workflow_item_id.in_(group_ids)).delete(
            synchronize_session=False
        )
        existing_sources = {
            (evidence.source_type, evidence.source_id) for evidence in primary.evidences
        }
        for duplicate in group[1:]:
            for evidence in list(duplicate.evidences):
                source_key = (evidence.source_type, evidence.source_id)
                if source_key in existing_sources:
                    db.delete(evidence)
                else:
                    evidence.workflow_item = primary
                    existing_sources.add(source_key)
                    moved_evidences += 1
            for event in list(duplicate.state_events):
                event.workflow_item = primary
            db.delete(duplicate)
            merged_items += 1
        primary.updated_at = datetime.now()
    if merged_items:
        db.flush()
        evaluate_workflow_alerts(db)
    db.commit()
    return {"merged_items": merged_items, "moved_evidences": moved_evidences}


def _email_actions(email: Optional[EmailMessage]) -> list[str]:
    if not email:
        return []
    try:
        payload = json.loads(email.action_items_json or "[]")
        return [str(item).strip() for item in payload if str(item).strip()]
    except (TypeError, json.JSONDecodeError):
        return []


def _decision(
    activity: ActivityLog,
    text: str,
    email: Optional[EmailMessage] = None,
    actions: Optional[list[str]] = None,
) -> tuple[str, str, str]:
    lowered = text.casefold()
    next_action = _plain(activity.next_action)
    explicitly_completed = any(term in lowered for term in COMPLETION_TERMS) and not any(
        term in lowered for term in NEGATIVE_COMPLETION_TERMS
    )
    # 一封邮件可能同时说明“某步骤已完成”和“整体仍需继续推进”。
    # 只在没有后续责任动作时，将整个事项标记为疑似完成。
    if explicitly_completed and not next_action:
        return "疑似完成", "我方", "新证据明确提到完成或解决，等待人工确认"
    if email:
        from app.services.email_intelligence import _is_internal_forward, _is_srun_sender

        recipients = json.loads(email.recipients_json or "[]")
        customer_has_request = bool(email.customer_request or actions)
        if (
            (not _is_srun_sender(email.sender) or _is_internal_forward(email.subject, email.sender, recipients))
            and customer_has_request
        ):
            return "处理中", "我方", "客户来信或内部转发包含明确诉求，下一步由我方处理"
    if next_action == "等待客户反馈":
        return "等待外部", "客户", "后续行动依赖客户反馈"
    if next_action in {"等待合同签订", "等待验收"}:
        return "等待外部", "第三方", f"后续行动为{next_action}"
    if next_action == "等待内部审批":
        return "处理中", "我方", "事项正在等待内部协同"
    if next_action == "我方处理":
        return "处理中", "我方", "新证据明确下一步由我方处理"
    if activity.blocker_flag:
        return "处理中", "我方", "活动包含阻塞证据，需要我方持续处理"
    return "处理中", "我方", "收到与事项相关的新推进证据"


def _record_state(
    db: Session,
    item: WorkflowItem,
    to_status: str,
    *,
    source: str,
    reason: str,
    confidence: Optional[float],
    evidence_id: Optional[UUID] = None,
    changed_by: Optional[UUID] = None,
) -> None:
    if to_status not in VALID_STATUSES:
        raise ValueError("不支持的流程状态")
    from_status = item.status
    if from_status == to_status:
        return
    item.status = to_status
    item.updated_at = datetime.now()
    item.completed_at = datetime.now() if to_status == "已完成" else None
    db.add(WorkflowStateEvent(
        workflow_item_id=item.id,
        from_status=from_status,
        to_status=to_status,
        source=source,
        reason=reason[:2000] if reason else None,
        confidence=confidence,
        evidence_id=evidence_id,
        changed_by=changed_by,
        occurred_at=datetime.now(),
    ))


def ingest_activity_evidence(
    db: Session,
    activity: ActivityLog,
    *,
    email: Optional[EmailMessage] = None,
    source_object_id: Optional[UUID] = None,
    confidence: Optional[float] = None,
    reason: Optional[str] = None,
) -> Optional[WorkflowItem]:
    """把可靠活动转换为事项，或作为新证据推进同一事项。"""
    if not activity.project_id:
        return None
    actions = _email_actions(email)
    actionable = bool(activity.next_action or activity.blocker_flag or actions)
    if not actionable:
        return None

    confidence = 1.0 if confidence is None else max(0.0, min(float(confidence), 1.0))
    if confidence < 0.8:
        return None
    source_type = _plain(activity.source) or "活动"
    source_id = source_object_id or (email.id if email else activity.id)
    title = _short(email.subject if email else (actions[0] if actions else activity.activity_content), 300)
    description_parts = [activity.activity_content]
    if actions:
        description_parts.append("；".join(actions))
    description = _short("\n".join(part for part in description_parts if part), 4000)
    topic_key = _topic_key(activity, email, title)
    evidence_at = activity.occurred_at or datetime.now()
    desired_status, responsibility_party, decision_reason = _decision(
        activity, description, email=email, actions=actions
    )

    item = (
        db.query(WorkflowItem)
        .filter(
            WorkflowItem.project_id == activity.project_id,
            WorkflowItem.topic_key == topic_key,
            WorkflowItem.status.in_(OPEN_STATUSES | {"已完成"}),
        )
        .order_by(WorkflowItem.updated_at.desc())
        .first()
    )
    created = False
    if not item:
        initial_status = "AI待确认" if confidence < 0.92 else (
            "待接收" if desired_status == "处理中" else desired_status
        )
        item = WorkflowItem(
            project_id=activity.project_id,
            owner_id=activity.owner_id,
            title=title,
            description=description,
            topic_key=topic_key,
            status=initial_status,
            responsibility_party=responsibility_party,
            priority="高" if activity.blocker_flag else "普通",
            due_date=activity.next_action_deadline,
            source_type=source_type,
            source_id=source_id,
            ai_generated=source_type != "手工录入",
            ai_confidence=confidence,
            ai_reason=(reason or decision_reason)[:2000],
            last_progress_at=evidence_at,
        )
        db.add(item)
        db.flush()
        db.add(WorkflowStateEvent(
            workflow_item_id=item.id,
            from_status=None,
            to_status=item.status,
            source="ai" if item.ai_generated else "manual",
            reason=item.ai_reason,
            confidence=confidence,
            occurred_at=datetime.now(),
        ))
        created = True

    existing_evidence = (
        db.query(WorkflowEvidence)
        .filter(
            WorkflowEvidence.workflow_item_id == item.id,
            WorkflowEvidence.source_type == source_type,
            WorkflowEvidence.source_id == source_id,
        )
        .first()
    )
    if existing_evidence:
        return item

    evidence = WorkflowEvidence(
        workflow_item_id=item.id,
        source_type=source_type,
        source_id=source_id,
        activity_id=activity.id,
        evidence_at=evidence_at,
        summary=description,
        decision="创建事项" if created else desired_status,
        confidence=confidence,
        reason=(reason or decision_reason)[:2000],
    )
    db.add(evidence)
    db.flush()

    if not created and confidence >= 0.92:
        # 已完成事项收到同主题新行动时自动重开；完成证据只进入“疑似完成”。
        target_status = desired_status
        if item.status == "已完成" and desired_status != "疑似完成":
            target_status = "处理中"
        _record_state(
            db, item, target_status, source="ai_evidence", reason=decision_reason,
            confidence=confidence, evidence_id=evidence.id,
        )
    item.description = description
    item.responsibility_party = responsibility_party
    item.last_progress_at = max(item.last_progress_at, evidence_at)
    if activity.next_action_deadline:
        item.due_date = activity.next_action_deadline
    if activity.blocker_flag:
        item.priority = "高"
    item.updated_at = datetime.now()
    return item


def transition_item(
    db: Session,
    item: WorkflowItem,
    to_status: str,
    *,
    changed_by: UUID,
    note: Optional[str],
) -> WorkflowItem:
    _record_state(
        db, item, to_status, source="manual", reason=(note or "人工办理"),
        confidence=1.0, changed_by=changed_by,
    )
    if to_status not in CLOSED_STATUSES:
        item.last_progress_at = datetime.now()
    return item


def _elapsed_days(value: datetime, now: datetime) -> int:
    if value.tzinfo and not now.tzinfo:
        value = value.replace(tzinfo=None)
    if now.tzinfo and not value.tzinfo:
        now = now.replace(tzinfo=None)
    return max((now - value).days, 0)


def _alert_level(elapsed: int, reminder: int, warning: int, escalation: int) -> Optional[tuple[str, int]]:
    if elapsed >= escalation:
        return "严重", escalation
    if elapsed >= warning:
        return "告警", warning
    if elapsed >= reminder:
        return "提醒", reminder
    return None


def evaluate_workflow_alerts(db: Session, now: Optional[datetime] = None) -> dict[str, int]:
    """重新计算所有未关闭事项；不满足条件的旧告警自动解除。"""
    now = now or datetime.now()
    thresholds = get_thresholds()
    active_keys: set[str] = set()
    created = updated = resolved = 0

    def upsert(
        item: WorkflowItem,
        alert_type: str,
        level: str,
        threshold_days: int,
        elapsed_days: int,
        message: str,
    ) -> None:
        nonlocal created, updated
        key = f"workflow:{item.id}:{alert_type}"
        active_keys.add(key)
        alert = db.query(WorkflowAlert).filter(WorkflowAlert.condition_key == key).first()
        if not alert:
            alert = WorkflowAlert(
                condition_key=key,
                workflow_item_id=item.id,
                project_id=item.project_id,
                alert_type=alert_type,
                level=level,
                status="活跃",
                threshold_days=threshold_days,
                elapsed_days=elapsed_days,
                message=message,
                evidence_at=item.last_progress_at,
                first_triggered_at=now,
                last_evaluated_at=now,
            )
            db.add(alert)
            created += 1
        else:
            alert.level = level
            alert.status = "活跃"
            alert.threshold_days = threshold_days
            alert.elapsed_days = elapsed_days
            alert.message = message
            alert.evidence_at = item.last_progress_at
            alert.last_evaluated_at = now
            alert.resolved_at = None
            updated += 1

    items = db.query(WorkflowItem).filter(WorkflowItem.status.in_(OPEN_STATUSES)).all()
    for item in items:
        project_name = item.project.project_name if item.project else "未知项目"
        if item.due_date:
            overdue = (now.date() - item.due_date).days
            result = _alert_level(
                overdue,
                0,
                thresholds["workflow_due_warning_grace_days"],
                thresholds["workflow_due_escalation_days"],
            )
            if result:
                level, threshold = result
                upsert(
                    item, "事项逾期", level, threshold, max(overdue, 0),
                    f"项目「{project_name}」事项《{item.title}》已超过截止日期{max(overdue, 0)}天",
                )
        elapsed = _elapsed_days(item.last_progress_at, now)
        if item.status == "等待外部":
            result = _alert_level(
                elapsed,
                thresholds["workflow_external_wait_reminder_days"],
                thresholds["workflow_external_wait_warning_days"],
                thresholds["workflow_external_wait_escalation_days"],
            )
            if result:
                level, threshold = result
                upsert(
                    item, "等待外部", level, threshold, elapsed,
                    f"项目「{project_name}」事项《{item.title}》等待外部反馈已{elapsed}天",
                )
        else:
            result = _alert_level(
                elapsed,
                thresholds["workflow_no_progress_reminder_days"],
                thresholds["workflow_no_progress_warning_days"],
                thresholds["workflow_no_progress_escalation_days"],
            )
            if result:
                level, threshold = result
                upsert(
                    item, "事项无推进", level, threshold, elapsed,
                    f"项目「{project_name}」事项《{item.title}》已{elapsed}天没有新的有效推进证据",
                )

    for alert in db.query(WorkflowAlert).filter(WorkflowAlert.status == "活跃").all():
        if alert.condition_key not in active_keys:
            alert.status = "已解除"
            alert.resolved_at = now
            alert.last_evaluated_at = now
            resolved += 1
    db.flush()
    return {"created": created, "updated": updated, "resolved": resolved}
