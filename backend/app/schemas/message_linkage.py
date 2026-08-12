"""消息中心连接与业务联动配置。"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


MessagePriority = Literal["low", "normal", "high", "urgent"]
RouteMode = Literal["ai", "user", "employee_group"]


class MessageLinkageRule(BaseModel):
    """一个业务场景如何提交给统一消息中心。"""

    scene_key: str = Field(..., min_length=2, max_length=64)
    scene_name: str = Field(..., min_length=2, max_length=50)
    business_domain: str = Field(..., min_length=2, max_length=30)
    description: str = Field("", max_length=240)
    enabled: bool = False
    category: str = Field("general", min_length=2, max_length=40)
    source_category: str = Field(..., min_length=2, max_length=64)
    priority: MessagePriority = "normal"
    route_mode: RouteMode = "ai"
    target_id: Optional[str] = Field(None, max_length=100)
    target_name: Optional[str] = Field(None, max_length=100)
    rollout_status: str = Field("待接入", max_length=30)

    @field_validator("target_id", "target_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class MessageLinkageConfigUpdate(BaseModel):
    """页面保存的完整配置；Token 留空表示保留原值。"""

    enabled: bool = False
    base_url: str = Field(..., min_length=8, max_length=300)
    api_key: Optional[str] = Field(None, max_length=500)
    clear_api_key: bool = False
    source_system: str = Field(..., min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    timeout_seconds: int = Field(10, ge=3, le=30)
    linkage_rules: list[MessageLinkageRule]

    @field_validator("base_url", "source_system", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        return str(value or "").strip()

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class MessageLinkageConfigView(BaseModel):
    enabled: bool
    base_url: str
    api_key_configured: bool
    source_system: str
    timeout_seconds: int
    linkage_rules: list[MessageLinkageRule]
    updated_at: Optional[datetime] = None


class MessageCenterHealthResult(BaseModel):
    success: bool
    message: str
    base_url: str
    response_time_ms: Optional[int] = None
    remote_status: Optional[str] = None
