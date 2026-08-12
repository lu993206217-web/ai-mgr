"""活动时间轴的展示层结构。

业务事实仍保存在 ActivityLog 与 EmailMessage 中；这里仅定义面向页面的结构化视图。
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EmailActivityDetail(BaseModel):
    """邮件活动的结构化详情，避免页面解析长文本。"""

    email_id: UUID
    communication_type: str
    subject: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    customer_request: Optional[str] = None
    customer_attitude: Optional[str] = None
    action_items: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    body_excerpt: Optional[str] = None
    attachment_names: list[str] = Field(default_factory=list)
