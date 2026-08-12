"""邮件情报模型。

原始邮件与 AI/规则分析结果分层保存。原文只追加，项目归属和分析结果可重新生成。
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_email_provider_external_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="manual", index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    internet_message_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    subject: Mapped[str] = mapped_column(String(1000), nullable=False, default="（无主题）")
    sender: Mapped[str] = mapped_column(String(500), nullable=False)
    recipients_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    cc_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    raw_headers_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    raw_body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    match_status: Mapped[str] = mapped_column(String(30), nullable=False, default="待确认", index=True)
    match_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    analysis_status: Mapped[str] = mapped_column(String(30), nullable=False, default="待分析", index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_request: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_attitude: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    risks_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    analysis_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    activity_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("activity_logs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project")
    attachments = relationship(
        "EmailAttachment", back_populates="email", cascade="all, delete-orphan"
    )


class EmailAttachment(Base):
    __tablename__ = "email_attachments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email_id: Mapped[UUID] = mapped_column(
        ForeignKey("email_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_attachment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    extraction_status: Mapped[str] = mapped_column(String(30), nullable=False, default="待提取")
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    email = relationship("EmailMessage", back_populates="attachments")


class EmailMatchAudit(Base):
    """邮件项目归属变更审计。"""

    __tablename__ = "email_match_audits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email_id: Mapped[UUID] = mapped_column(
        ForeignKey("email_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 审计记录保留历史 UUID，不随项目删除而丢失。
    old_project_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    new_project_id: Mapped[UUID] = mapped_column(nullable=False)
    change_method: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
