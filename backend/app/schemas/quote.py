"""
报价 Schema

软件报价单的 Pydantic 模型。
支持多产品授权 + 实施服务的复杂报价结构。
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


# ============ 授权明细项 ============
class LicenseItem(BaseModel):
    """软件授权明细项"""
    product_name: str = Field(..., min_length=1, max_length=200)
    version: Optional[str] = Field(None, max_length=50)
    license_type: str = Field(..., description="授权类型: perpetual/annual_subscription/concurrent/named")
    qty: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    subtotal: Decimal = Field(default=Decimal("0"), ge=0)
    description: Optional[str] = Field(None, max_length=500)


# ============ 服务明细项 ============
class ServiceItem(BaseModel):
    """实施服务明细项"""
    service_type: str = Field(..., description="服务类型: implementation/training/customization/data_migration/integration/support")
    description: Optional[str] = Field(None, max_length=500)
    quantity: int = Field(default=1, ge=0)  # 天数或人天
    daily_rate: Decimal = Field(default=Decimal("0"), ge=0)  # 人天费率
    subtotal: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = Field(None, max_length=300)


# ============ 基础 Schema ============
class QuoteBase(BaseModel):
    """报价基础 Schema"""
    customer_id: UUID
    project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None

    quote_no: Optional[str] = Field(None, max_length=50)
    quote_title: str = Field(..., min_length=1, max_length=300)
    quote_date: date
    valid_until: Optional[date] = None
    currency: str = Field(default="USD", max_length=10)

    # 授权明细
    license_items: List[LicenseItem] = Field(default_factory=list)
    license_subtotal: Decimal = Field(default=Decimal("0"), ge=0)

    # 服务明细
    service_items: List[ServiceItem] = Field(default_factory=list)
    service_subtotal: Decimal = Field(default=Decimal("0"), ge=0)

    # 汇总
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    grand_total: Decimal = Field(default=Decimal("0"), ge=0)


class QuoteCreate(QuoteBase):
    """报价创建 Schema（owner_id 由后端自动填充）"""
    internal_notes: Optional[str] = Field(None, max_length=2000)
    customer_notes: Optional[str] = Field(None, max_length=2000)


class QuoteUpdate(BaseModel):
    """报价更新 Schema"""
    customer_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None

    quote_title: Optional[str] = Field(None, min_length=1, max_length=300)
    quote_date: Optional[date] = None
    valid_until: Optional[date] = None
    status: Optional[str] = Field(None, max_length=20)
    currency: Optional[str] = Field(None, max_length=10)

    license_items: Optional[List[LicenseItem]] = None
    license_subtotal: Optional[Decimal] = Field(None, ge=0)
    service_items: Optional[List[ServiceItem]] = None
    service_subtotal: Optional[Decimal] = Field(None, ge=0)

    discount_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    grand_total: Optional[Decimal] = Field(None, ge=0)

    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None


class QuoteInDB(QuoteBase):
    """报价数据库 Schema"""
    id: UUID
    quote_no: str
    status: str
    owner_id: UUID

    attachment_url: Optional[str] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    class Config:
        from_attributes = True


class Quote(QuoteInDB):
    """报价响应 Schema"""
    customer_name: Optional[str] = None
    project_name: Optional[str] = None
    channel_name: Optional[str] = None
    owner_name: Optional[str] = None
