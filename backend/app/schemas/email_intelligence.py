"""邮件情报 API Schema。"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ManualEmailIngest(BaseModel):
    external_id: Optional[str] = None
    thread_id: Optional[str] = None
    subject: str = Field(default="（无主题）", max_length=1000)
    sender: str = Field(..., min_length=3, max_length=500)
    recipients: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    received_at: datetime
    body_text: str = Field(default="", max_length=200000)
    body_html: Optional[str] = Field(default=None, max_length=500000)


class EmailAttachment(BaseModel):
    id: UUID
    file_name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    extraction_status: str
    document_type: Optional[str] = None
    summary: Optional[str] = None

    model_config = {"from_attributes": True}


class EmailMessage(BaseModel):
    id: UUID
    provider: str
    external_id: str
    thread_id: Optional[str] = None
    subject: str
    sender: str
    recipients: List[str]
    cc: List[str]
    received_at: datetime
    body_text: str
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    match_status: str
    match_method: Optional[str] = None
    match_score: Optional[float] = None
    analysis_status: str
    summary: Optional[str] = None
    customer_request: Optional[str] = None
    customer_attitude: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    activity_id: Optional[UUID] = None
    attachments: List[EmailAttachment] = Field(default_factory=list)
    created_at: datetime


class EmailBindRequest(BaseModel):
    project_id: UUID
    create_activity: bool = True
    reason: Optional[str] = Field(default=None, max_length=500)


class EmailAnalysisUpdate(BaseModel):
    summary: Optional[str] = None
    customer_request: Optional[str] = None
    customer_attitude: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class EmailConnectionStatus(BaseModel):
    provider: str = "gmail"
    configured: bool
    connected: bool = False
    account_email: Optional[str] = None
    message: str
    receive_host: Optional[str] = None
    receive_port: Optional[int] = None
    send_host: Optional[str] = None
    send_port: Optional[int] = None


class EmailConnections(BaseModel):
    providers: List[EmailConnectionStatus] = Field(default_factory=list)


class DingTalkMailSyncRequest(BaseModel):
    max_messages: int = Field(default=50, ge=1, le=200)
    unseen_only: bool = False


class DingTalkMailConfig(BaseModel):
    enabled: bool = False
    account_email: Optional[str] = None
    password_configured: bool = False
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    inbox_folder: str = "INBOX"
    sent_folder: Optional[str] = None


class DingTalkMailConfigUpdate(BaseModel):
    enabled: bool = True
    account_email: str = Field(default="", max_length=200)
    app_password: Optional[str] = Field(default=None, min_length=4, max_length=300)
    sent_folder: Optional[str] = Field(default=None, max_length=200)
    clear_password: bool = False


class DingTalkMailSyncResult(BaseModel):
    folders: List[str] = Field(default_factory=list)
    scanned_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    matched_count: int = 0
    activity_count: int = 0
    failed_count: int = 0
    errors: List[str] = Field(default_factory=list)
