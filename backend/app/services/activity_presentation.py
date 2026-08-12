"""为活动时间轴生成简洁、结构化的邮件展示信息。"""
import json
import re
from email.utils import parseaddr
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.email_intelligence import EmailMessage
from app.schemas.activity_presentation import EmailActivityDetail
from app.services.mail_runtime_config import get_dingtalk_mail_config


def _source_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _json_list(value: Optional[str]) -> list[str]:
    try:
        data = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []


def _email_domain(value: str) -> str:
    address = parseaddr(value or "")[1].casefold()
    return address.rsplit("@", 1)[1] if "@" in address else ""


def _internal_domains() -> set[str]:
    domains = {"srun.com"}
    try:
        account = get_dingtalk_mail_config().account_email
    except (OSError, ValueError):
        account = ""
    account_domain = _email_domain(account)
    if account_domain:
        domains.add(account_domain)
    return domains


def _is_internal_address(value: str, domains: set[str]) -> bool:
    domain = _email_domain(value)
    return any(domain == item or domain.endswith(f".{item}") for item in domains)


def _email_flow(email: EmailMessage, domains: set[str]) -> str:
    """返回 inbound / outbound / internal。"""
    if not _is_internal_address(email.sender, domains):
        return "inbound"
    recipients = _json_list(email.recipients_json)
    if recipients and all(_is_internal_address(item, domains) for item in recipients):
        return "internal"
    return "outbound"


def _communication_type(db: Session, email: EmailMessage, domains: set[str]) -> str:
    flow = _email_flow(email, domains)
    if flow == "internal":
        return "内部协同"

    previous: list[EmailMessage] = []
    if email.thread_id:
        previous = (
            db.query(EmailMessage)
            .filter(
                EmailMessage.thread_id == email.thread_id,
                EmailMessage.id != email.id,
                EmailMessage.received_at < email.received_at,
            )
            .order_by(EmailMessage.received_at.desc())
            .all()
        )
    previous_flows = {_email_flow(item, domains) for item in previous}
    if flow == "outbound":
        return "我方回复" if "inbound" in previous_flows else "我方发起"
    return "客户回复" if "outbound" in previous_flows else "客户发起"


def _brief(value: Optional[str], limit: int = 150) -> str:
    clean = re.sub(r"\s+", " ", value or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip("，,。；; ") + "…"


def _requires_srun_action(email: EmailMessage, communication_type: str) -> bool:
    if communication_type in {"客户发起", "客户回复"}:
        return True
    actions = _json_list(email.action_items_json)
    return bool(
        communication_type == "内部协同"
        and email.customer_request
        and actions
        and actions[0].startswith("等待客户反馈")
    )


def _display_actions(email: EmailMessage, requires_srun_action: bool) -> list[str]:
    actions = _json_list(email.action_items_json)
    if not requires_srun_action:
        return actions
    # 旧分析中把客户来信错误写成“等待客户反馈”的合成项，只修正展示层，原始分析仍保留。
    while actions and actions[0].startswith("等待客户反馈"):
        actions.pop(0)
    if not actions and email.customer_request:
        actions.append(email.customer_request)
    return actions


def enrich_activity_presentation(db: Session, activity: ActivityLog, target: Any) -> Any:
    """给 Pydantic 响应对象补充展示标题、短摘要和邮件结构化详情。"""
    if _source_value(activity.source) not in {"邮件", "EMAIL"}:
        target.display_summary = _brief(activity.activity_content, 180)
        return target

    email = (
        db.query(EmailMessage)
        .filter(
            (EmailMessage.activity_id == activity.id)
            | (EmailMessage.id == activity.source_id)
        )
        .first()
    )
    if not email:
        target.display_title = "邮件动态"
        target.display_summary = _brief(activity.activity_content)
        return target

    domains = _internal_domains()
    communication_type = _communication_type(db, email, domains)
    requires_srun_action = _requires_srun_action(email, communication_type)
    action_items = _display_actions(email, requires_srun_action)
    if requires_srun_action:
        target.next_action = "我方处理"
    recipients = _json_list(email.recipients_json)
    cc = _json_list(email.cc_json)
    summary = email.summary or email.subject or activity.activity_content
    body_excerpt = _brief(email.raw_body_text, 2000) or None
    target.display_title = communication_type
    target.display_summary = _brief(summary)
    target.email_detail = EmailActivityDetail(
        email_id=email.id,
        communication_type=communication_type,
        subject=email.subject,
        sender=email.sender,
        recipients=recipients,
        cc=cc,
        summary=email.summary,
        customer_request=email.customer_request,
        customer_attitude=email.customer_attitude,
        action_items=action_items,
        risks=_json_list(email.risks_json),
        body_excerpt=body_excerpt,
        attachment_names=[item.file_name for item in email.attachments],
    )
    return target
