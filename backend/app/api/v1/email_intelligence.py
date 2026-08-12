"""AI 邮件情报中心 API。"""
import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.email_intelligence import EmailMatchAudit, EmailMessage as EmailMessageModel
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PaginatedResponse, Response
from app.schemas.email_intelligence import (
    EmailAnalysisUpdate,
    EmailBindRequest,
    EmailConnectionStatus,
    EmailConnections,
    DingTalkMailConfig,
    DingTalkMailConfigUpdate,
    DingTalkMailSyncRequest,
    DingTalkMailSyncResult,
    EmailMessage,
    ManualEmailIngest,
)
from app.services.email_intelligence import analyze_and_match_email, create_project_activity
from app.services.dingtalk_mail import DingTalkMailService
from app.services.mail_runtime_config import get_dingtalk_mail_config, save_dingtalk_mail_config

router = APIRouter(tags=["AI邮件情报"])
EMAIL_MANAGER_ROLES = {"管理员", "项目经理"}


def _is_email_manager(user: User) -> bool:
    return user.role in EMAIL_MANAGER_ROLES


def _require_email_manager(user: User) -> None:
    if not _is_email_manager(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员或项目经理可执行邮件导入、分析和项目归属操作",
        )


def _to_schema(item: EmailMessageModel) -> EmailMessage:
    return EmailMessage(
        id=item.id,
        provider=item.provider,
        external_id=item.external_id,
        thread_id=item.thread_id,
        subject=item.subject,
        sender=item.sender,
        recipients=json.loads(item.recipients_json or "[]"),
        cc=json.loads(item.cc_json or "[]"),
        received_at=item.received_at,
        body_text=item.raw_body_text,
        project_id=item.project_id,
        project_name=item.project.project_name if item.project else None,
        match_status=item.match_status,
        match_method=item.match_method,
        match_score=item.match_score,
        analysis_status=item.analysis_status,
        summary=item.summary,
        customer_request=item.customer_request,
        customer_attitude=item.customer_attitude,
        action_items=json.loads(item.action_items_json or "[]"),
        risks=json.loads(item.risks_json or "[]"),
        activity_id=item.activity_id,
        attachments=item.attachments,
        created_at=item.created_at,
    )


@router.get("/connection", response_model=Response[EmailConnectionStatus])
async def connection_status(current_user: User = Depends(get_current_user)) -> Any:
    configured = bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)
    message = "Gmail OAuth 参数已配置，可进入授权流程" if configured else "等待配置 Google OAuth 客户端信息"
    return Response.success(
        data=EmailConnectionStatus(
            configured=configured,
            account_email=settings.GMAIL_ACCOUNT_EMAIL,
            message=message,
        )
    )


@router.get("/connections", response_model=Response[EmailConnections])
async def connection_statuses(current_user: User = Depends(get_current_user)) -> Any:
    """查看 Gmail 与钉钉企业邮箱接入状态，不返回任何密码。"""
    gmail_configured = bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)
    dingtalk_service = DingTalkMailService()
    providers = [
        EmailConnectionStatus(
            provider="gmail",
            configured=gmail_configured,
            account_email=settings.GMAIL_ACCOUNT_EMAIL,
            message="Gmail OAuth 参数已配置" if gmail_configured else "等待配置 Google OAuth 客户端信息",
        ),
        EmailConnectionStatus(
            provider="dingtalk_mail",
            configured=dingtalk_service.configured,
            connected=False,
            account_email=dingtalk_service.account or None,
            message=(
                "钉钉企业邮箱已配置，可测试连接并同步"
                if dingtalk_service.configured and dingtalk_service.enabled
                else "等待配置邮箱账号、客户端专用密码/授权码并启用"
            ),
            receive_host=settings.DINGTALK_MAIL_IMAP_HOST,
            receive_port=settings.DINGTALK_MAIL_IMAP_PORT,
            send_host=settings.DINGTALK_MAIL_SMTP_HOST,
            send_port=settings.DINGTALK_MAIL_SMTP_PORT,
        ),
    ]
    return Response.success(data=EmailConnections(providers=providers))


def _dingtalk_config_schema() -> DingTalkMailConfig:
    config = get_dingtalk_mail_config()
    return DingTalkMailConfig(
        enabled=config.enabled,
        account_email=config.account_email or None,
        password_configured=bool(config.app_password),
        imap_host=settings.DINGTALK_MAIL_IMAP_HOST,
        imap_port=settings.DINGTALK_MAIL_IMAP_PORT,
        smtp_host=settings.DINGTALK_MAIL_SMTP_HOST,
        smtp_port=settings.DINGTALK_MAIL_SMTP_PORT,
        inbox_folder=config.inbox_folder,
        sent_folder=config.sent_folder,
    )


@router.get("/providers/dingtalk/config", response_model=Response[DingTalkMailConfig])
def get_dingtalk_mail_config_view(
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    return Response.success(data=_dingtalk_config_schema(), message="获取成功")


@router.put("/providers/dingtalk/config", response_model=Response[DingTalkMailConfig])
def update_dingtalk_mail_config(
    payload: DingTalkMailConfigUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    try:
        save_dingtalk_mail_config(
            enabled=payload.enabled,
            account_email=payload.account_email,
            app_password=payload.app_password,
            sent_folder=payload.sent_folder,
            clear_password=payload.clear_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response.success(
        data=_dingtalk_config_schema(),
        message="企业邮箱配置已保存；安全密码不会回显",
    )


@router.post("/providers/dingtalk/test", response_model=Response[EmailConnectionStatus])
def test_dingtalk_mail_connection(
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    service = DingTalkMailService()
    try:
        result = service.test_connections()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"钉钉邮箱连接失败：{exc}") from exc
    connected = bool(result.get("imap") and result.get("smtp"))
    return Response.success(
        data=EmailConnectionStatus(
            provider="dingtalk_mail",
            configured=service.configured,
            connected=connected,
            account_email=service.account or None,
            message="IMAP 收件与 SMTP 发件连接均验证成功" if connected else "邮箱连接未完全通过",
            receive_host=settings.DINGTALK_MAIL_IMAP_HOST,
            receive_port=settings.DINGTALK_MAIL_IMAP_PORT,
            send_host=settings.DINGTALK_MAIL_SMTP_HOST,
            send_port=settings.DINGTALK_MAIL_SMTP_PORT,
        )
    )


@router.post("/providers/dingtalk/sync", response_model=Response[DingTalkMailSyncResult])
def sync_dingtalk_mail(
    payload: DingTalkMailSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    service = DingTalkMailService()
    try:
        result = service.sync(db, max_messages=payload.max_messages, unseen_only=payload.unseen_only)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"钉钉邮箱同步失败：{exc}") from exc
    return Response.success(data=DingTalkMailSyncResult(**result), message="钉钉企业邮箱同步完成")


@router.get("", response_model=Response[PaginatedResponse[EmailMessage]])
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    match_status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = db.query(EmailMessageModel)
    if not _is_email_manager(current_user):
        owned_project_ids = db.query(Project.id).filter(Project.owner_id == current_user.id)
        query = query.filter(EmailMessageModel.project_id.in_(owned_project_ids))
    if match_status:
        query = query.filter(EmailMessageModel.match_status == match_status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            EmailMessageModel.subject.ilike(like) | EmailMessageModel.sender.ilike(like)
        )
    total = query.count()
    items = (
        query.order_by(EmailMessageModel.received_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Response.success(
        data=PaginatedResponse.create(
            items=[_to_schema(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/manual-ingest", response_model=Response[EmailMessage])
async def manual_ingest(
    payload: ManualEmailIngest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    external_id = payload.external_id or f"manual-{uuid4()}"
    existing = (
        db.query(EmailMessageModel)
        .filter(
            EmailMessageModel.provider == "manual",
            EmailMessageModel.external_id == external_id,
        )
        .first()
    )
    if existing:
        return Response.success(data=_to_schema(existing), message="邮件已存在，未重复导入")

    item = EmailMessageModel(
        provider="manual",
        external_id=external_id,
        thread_id=payload.thread_id,
        subject=payload.subject,
        sender=payload.sender,
        recipients_json=json.dumps(payload.recipients, ensure_ascii=False),
        cc_json=json.dumps(payload.cc, ensure_ascii=False),
        received_at=payload.received_at,
        raw_body_text=payload.body_text,
        raw_body_html=payload.body_html,
        match_status="待确认",
        analysis_status="待分析",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    intelligence = analyze_and_match_email(
        db,
        subject=payload.subject,
        sender=payload.sender,
        recipients=payload.recipients,
        cc=payload.cc,
        body=payload.body_text,
        received_at=payload.received_at,
        thread_id=payload.thread_id,
    )
    project = intelligence["project"]
    analysis = intelligence["analysis"]
    item.project_id = project.id if project else None
    item.match_status = "已自动关联" if project else "待确认"
    item.match_method = intelligence["match_method"]
    item.match_score = intelligence["match_score"]
    item.analysis_status = intelligence["analysis_status"]
    if not intelligence["should_create_activity"]:
        item.analysis_status += "（无需入活动）"
    item.summary = analysis["summary"]
    item.customer_request = analysis["customer_request"]
    item.customer_attitude = analysis["customer_attitude"]
    item.action_items_json = json.dumps(analysis["action_items"], ensure_ascii=False)
    item.risks_json = json.dumps(analysis["risks"], ensure_ascii=False)
    item.analysis_version = intelligence["analysis_version"]
    if project and intelligence["should_create_activity"]:
        create_project_activity(db, item)
    db.commit()
    db.refresh(item)
    return Response.success(data=_to_schema(item), message="原始邮件已保存并完成首轮分析")


@router.post("/{email_id}/bind", response_model=Response[EmailMessage])
async def bind_email(
    email_id: UUID,
    payload: EmailBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    item = db.query(EmailMessageModel).filter(EmailMessageModel.id == email_id).first()
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在")
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    old_project_id = item.project_id
    item.project_id = project.id
    item.match_status = "人工确认"
    item.match_method = "manual"
    item.match_score = 1.0
    item.updated_at = datetime.now(timezone.utc)
    if item.activity_id:
        activity = db.query(ActivityLog).filter(ActivityLog.id == item.activity_id).first()
        if activity:
            activity.project_id = project.id
            activity.owner_id = project.owner_id
            from app.services.workflow_center import ingest_activity_evidence

            ingest_activity_evidence(
                db,
                activity,
                email=item,
                source_object_id=item.id,
                confidence=1.0,
                reason="邮件项目归属经人工确认",
            )
    elif payload.create_activity and "无需入活动" not in (item.analysis_status or ""):
        create_project_activity(db, item)

    db.add(
        EmailMatchAudit(
            email_id=item.id,
            old_project_id=old_project_id,
            new_project_id=project.id,
            change_method="manual",
            reason=payload.reason,
            changed_by=current_user.id,
        )
    )

    affected_project_ids = {project.id}
    if old_project_id:
        affected_project_ids.add(old_project_id)
    for affected_id in affected_project_ids:
        affected = db.query(Project).filter(Project.id == affected_id).first()
        if affected:
            affected.last_activity_at = (
                db.query(func.max(ActivityLog.occurred_at))
                .filter(ActivityLog.project_id == affected_id)
                .scalar()
            )
            affected.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return Response.success(data=_to_schema(item), message="项目归属已确认")


@router.put("/{email_id}/analysis", response_model=Response[EmailMessage])
async def update_analysis(
    email_id: UUID,
    payload: EmailAnalysisUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    _require_email_manager(current_user)
    item = db.query(EmailMessageModel).filter(EmailMessageModel.id == email_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在")
    item.summary = payload.summary
    item.customer_request = payload.customer_request
    item.customer_attitude = payload.customer_attitude
    item.action_items_json = json.dumps(payload.action_items, ensure_ascii=False)
    item.risks_json = json.dumps(payload.risks, ensure_ascii=False)
    item.analysis_status = "人工修正"
    item.analysis_version = "manual"
    if item.activity_id:
        activity = db.query(ActivityLog).filter(ActivityLog.id == item.activity_id).first()
        if activity:
            from app.services.workflow_center import ingest_activity_evidence

            ingest_activity_evidence(
                db,
                activity,
                email=item,
                source_object_id=item.id,
                confidence=1.0,
                reason="邮件分析结果经人工修正",
            )
    db.commit()
    db.refresh(item)
    return Response.success(data=_to_schema(item), message="分析结果已更新，原始邮件未改变")
