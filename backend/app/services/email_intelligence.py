"""邮件项目匹配与活动生成服务。"""
import json
import re
import ssl
from datetime import datetime
from datetime import date
from typing import Any, Optional
from urllib.error import HTTPError, URLError
import urllib.request
from email.utils import parseaddr
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.email_intelligence import EmailMessage
from app.core.config import settings
from app.models.enums import ActivitySource, ActivityType, NextAction
from app.models.project import Project


def _normalize(value: str) -> str:
    return re.sub(r"[\s\-_—–·/\\()[\]（）]+", "", (value or "").casefold())


def _normalized_subject(subject: str) -> str:
    cleaned = re.sub(r"^\s*((re|fw|fwd)\s*:\s*)+", "", subject or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*\[[^\]]{1,40}\]\s*", "", cleaned)
    return _normalize(cleaned)


def _is_srun_sender(sender: str) -> bool:
    address = parseaddr(sender or "")[1].casefold()
    domain = address.rsplit("@", 1)[1] if "@" in address else ""
    return domain == "srun.com" or domain.endswith(".srun.com")


def _is_internal_forward(subject: str, sender: str, recipients: list[str]) -> bool:
    if not _is_srun_sender(sender) or not recipients:
        return False
    all_internal = all(_is_srun_sender(item) for item in recipients)
    return all_internal and bool(re.match(r"^\s*(转发|fw|fwd)\s*[:：]", subject or "", re.IGNORECASE))


def match_project(
    db: Session,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
) -> tuple[Optional[Project], Optional[str], Optional[float]]:
    """线程继承或主题精确匹配才自动关联，正文包含只作为待确认线索。"""
    if thread_id:
        inherited = (
            db.query(EmailMessage)
            .filter(
                EmailMessage.thread_id == thread_id,
                EmailMessage.project_id.isnot(None),
                EmailMessage.match_status.in_(("已自动关联", "人工确认")),
            )
            .order_by(EmailMessage.received_at.desc())
            .first()
        )
        if inherited and inherited.project:
            return inherited.project, "thread_inherited", 1.0

    normalized_subject = _normalized_subject(subject)
    exact_candidates = []
    body_haystack = _normalize(body)
    contains_candidate = False
    for project in db.query(Project).all():
        name = _normalize(project.project_name)
        if name and name == normalized_subject:
            exact_candidates.append(project)
        elif len(name) >= 4 and (name in normalized_subject or name in body_haystack):
            contains_candidate = True
    if len(exact_candidates) == 1:
        return exact_candidates[0], "subject_exact", 1.0
    if len(exact_candidates) > 1:
        return None, "ambiguous", None
    if contains_candidate:
        return None, "candidate_contains", 0.6
    return None, None, None


def basic_analyze(subject: str, body: str) -> dict:
    """无模型依赖的首期规则分析，后续可替换为可版本化 AI 分析器。"""
    clean = re.sub(r"\s+", " ", body or "").strip()
    summary = clean[:240] if clean else subject
    lowered = f"{subject} {body}".casefold()
    risk_words = ("delay", "blocked", "urgent", "延期", "阻塞", "紧急", "投诉", "失败")
    request_words = ("please", "request", "need", "要求", "请", "需要")
    risks = ["邮件中出现潜在风险关键词，请人工核实"] if any(word in lowered for word in risk_words) else []
    customer_request = summary if any(word in lowered for word in request_words) else None
    non_actionable_words = ("recall:", "撤回", "报销", "expense reimbursement")
    return {
        "summary": summary,
        "customer_request": customer_request,
        "customer_attitude": "待AI判断",
        "action_items": [],
        "risks": risks,
        "is_actionable": not any(word in lowered for word in non_actionable_words),
    }


class DeepSeekEmailAnalyzer:
    """将邮件原文分析为可重跑的结构化项目情报。"""

    def analyze(
        self,
        *,
        subject: str,
        sender: str,
        recipients: list[str],
        cc: list[str],
        body: str,
        received_at: datetime,
        projects: list[Project],
    ) -> dict[str, Any]:
        if not settings.EMAIL_AI_ENABLED:
            raise RuntimeError("邮件 AI 分析未启用")
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("DeepSeek API Key 未配置")
        candidates = [
            {
                "project_id": str(project.id),
                "project_name": project.project_name,
                "country": project.country,
                "customer": project.customer.customer_name if project.customer else None,
                "channel": project.channel.channel_name if project.channel else None,
                "stage": str(getattr(project.current_stage, "value", project.current_stage)),
            }
            for project in projects
        ]
        payload = {
            "email": {
                "subject": subject,
                "sender": sender,
                "recipients": recipients,
                "cc": cc,
                "received_at": received_at.isoformat(),
                "body": body[:30000],
            },
            "candidate_projects": candidates,
        }
        system_prompt = (
            "你是海外项目邮件情报分析器。只返回一个JSON对象，不要Markdown。"
            "原始邮件可能包含签名、免责声明和历史回复，应提取本次新增事实，不把签名当正文。"
            "project_id只能从candidate_projects选择；证据不足必须返回null，不得靠名称相似硬猜。"
            "confidence为0到1。summary应说明本次实际进展；customer_request提取客户明确诉求；"
            "customer_attitude只能为积极、中性、消极、未知；action_items必须是简短字符串数组；"
            "risks必须是有邮件原文依据的字符串数组。next_action只能为我方处理、等待客户反馈、等待内部审批、"
            "等待合同签订、等待验收、其他或null；next_action_deadline只能为YYYY-MM-DD或null。"
            "waiting_party表示下一步必须采取行动的一方，而不是邮件发送方。客户来信要求Srun处理或回复时，"
            "next_action必须为我方处理，waiting_party必须为我方（Srun）；只有我方已提出请求并等待客户补充时，"
            "才使用等待客户反馈。risk_reason没有明确风险时为null。"
            "is_actionable表示本次邮件是否包含值得进入项目时间轴的新业务事实；撤回通知、系统通知、"
            "签名空邮件、报销等非项目邮件必须为false。email_type返回客户来信、我方回复、内部转发、"
            "撤回通知、系统通知、非项目邮件或其他。"
            "返回字段：project_id,confidence,match_reason,summary,customer_request,customer_attitude,"
            "action_items,risks,next_action,next_action_deadline,waiting_party,risk_reason,is_actionable,email_type。"
        )
        request_body = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
            ],
            "temperature": settings.DEEPSEEK_TEMPERATURE,
            "max_tokens": min(settings.DEEPSEEK_MAX_TOKENS, 2048),
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            context = None if settings.DEEPSEEK_VERIFY_SSL else ssl._create_unverified_context()
            with urllib.request.urlopen(request, timeout=settings.DEEPSEEK_TIMEOUT, context=context) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek返回HTTP {exc.code}: {detail[:200]}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"DeepSeek调用失败: {exc}") from exc
        try:
            content = response_payload["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("DeepSeek返回的邮件分析不是有效JSON") from exc


def analyze_and_match_email(
    db: Session,
    *,
    subject: str,
    sender: str,
    recipients: list[str],
    cc: list[str],
    body: str,
    received_at: datetime,
    thread_id: Optional[str] = None,
) -> dict[str, Any]:
    """规则可靠匹配优先；DeepSeek高置信度才允许自动关联。"""
    projects = db.query(Project).all()
    project, method, score = match_project(db, subject, body, thread_id=thread_id)
    analysis = basic_analyze(subject, body)
    status = "规则初析"
    version = "rules-v1"
    try:
        ai = DeepSeekEmailAnalyzer().analyze(
            subject=subject,
            sender=sender,
            recipients=recipients,
            cc=cc,
            body=body,
            received_at=received_at,
            projects=projects,
        )
        action_items = [str(item).strip() for item in (ai.get("action_items") or []) if str(item).strip()]
        risks = [str(item).strip() for item in (ai.get("risks") or []) if str(item).strip()]
        next_action = str(ai.get("next_action") or "").strip()
        deadline = str(ai.get("next_action_deadline") or "").strip()
        waiting_party = str(ai.get("waiting_party") or "").strip()
        risk_reason = str(ai.get("risk_reason") or "").strip()
        customer_request = str(ai.get("customer_request") or "").strip()
        # 客户来信包含明确诉求时，下一步责任默认在我方；避免把“邮件发送方”误当成“等待对象”。
        if (
            (not _is_srun_sender(sender) or _is_internal_forward(subject, sender, recipients))
            and (customer_request or action_items)
            and next_action == NextAction.WAITING_CUSTOMER.value
        ):
            next_action = NextAction.OUR_ACTION.value
            waiting_party = "我方（Srun）"
        if next_action:
            detail = next_action
            if waiting_party:
                label = "责任方" if next_action == NextAction.OUR_ACTION.value else "等待对象"
                detail += f"（{label}：{waiting_party}）"
            if deadline:
                detail += f"，截止日期：{deadline}"
            action_items.insert(0, detail)
        if risk_reason and risk_reason not in risks:
            risks.append(risk_reason)
        analysis = {
            "summary": str(ai.get("summary") or analysis["summary"]).strip()[:4000],
            "customer_request": customer_request or None,
            "customer_attitude": str(ai.get("customer_attitude") or "未知").strip()[:50],
            "action_items": action_items[:20],
            "risks": risks[:20],
            "is_actionable": bool(ai.get("is_actionable", True)),
        }
        status = "AI已分析"
        version = f"{settings.DEEPSEEK_MODEL}-email-v2"
        if not project:
            candidate_id = ai.get("project_id")
            confidence = max(0.0, min(float(ai.get("confidence") or 0), 1.0))
            candidate = None
            try:
                candidate_uuid = UUID(str(candidate_id)) if candidate_id else None
                candidate = next((item for item in projects if item.id == candidate_uuid), None)
            except (TypeError, ValueError):
                candidate = None
            if candidate and confidence >= settings.EMAIL_AI_AUTO_MATCH_SCORE:
                project, method, score = candidate, "deepseek_reliable", confidence
            elif candidate:
                method, score = "deepseek_candidate", confidence
    except (RuntimeError, TypeError, ValueError):
        status = "规则初析（AI暂不可用）"
    return {
        "project": project,
        "match_method": method,
        "match_score": score,
        "analysis": analysis,
        "analysis_status": status,
        "analysis_version": version,
        "should_create_activity": bool(analysis.get("is_actionable", True)),
    }


def create_project_activity(db: Session, email: EmailMessage) -> Optional[ActivityLog]:
    if not email.project_id or email.activity_id:
        return None
    project = db.query(Project).filter(Project.id == email.project_id).first()
    if not project:
        return None
    # 活动主表只保存便于检索的短摘要；诉求、行动项、风险和原文继续保存在邮件情报层，
    # 由活动详情按结构展示，避免时间轴被长文本淹没。
    content = re.sub(r"\s+", " ", email.summary or email.subject).strip()
    action_items = json.loads(email.action_items_json or "[]")
    risks = json.loads(email.risks_json or "[]")
    first_action = str(action_items[0]) if action_items else ""
    next_action = next(
        (item for item in NextAction if item.value in first_action),
        NextAction.OTHER if first_action else None,
    )
    deadline_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", first_action)
    deadline = None
    if deadline_match:
        try:
            deadline = date.fromisoformat(deadline_match.group(1))
        except ValueError:
            deadline = None
    activity = ActivityLog(
        project_id=project.id,
        activity_type=ActivityType.PROGRESS_UPDATE,
        activity_content=content[:500],
        next_action=next_action,
        next_action_deadline=deadline,
        # AI/规则风险只是建议，未经人工确认不得影响项目健康度。
        blocker_flag=False,
        owner_id=project.owner_id,
        source=ActivitySource.EMAIL,
        source_id=email.id,
        occurred_at=email.received_at,
    )
    db.add(activity)
    db.flush()
    email.activity_id = activity.id
    email_timestamp = email.received_at.replace(tzinfo=None) if email.received_at.tzinfo else email.received_at
    project_timestamp = project.last_activity_at
    if project_timestamp and project_timestamp.tzinfo:
        project_timestamp = project_timestamp.replace(tzinfo=None)
    if not project_timestamp or email_timestamp > project_timestamp:
        project.last_activity_at = email.received_at
        project.updated_at = datetime.now()
    # 邮件活动生成后立即进入流程中心。流程中心只读取结构化分析结果，不改原始邮件。
    from app.services.workflow_center import ingest_activity_evidence

    ingest_activity_evidence(
        db,
        activity,
        email=email,
        source_object_id=email.id,
        confidence=float(email.match_score or 1),
        reason=f"邮件分析：{email.analysis_status}",
    )
    return activity
