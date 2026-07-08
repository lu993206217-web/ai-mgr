"""
客户 Schema

客户管理的 Pydantic 模型。
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


# ============ 基础 Schema ============
class CustomerBase(BaseModel):
    """客户基础 Schema"""
    customer_name: str = Field(..., min_length=1, max_length=200)
    country: str = Field(..., min_length=1, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    customer_type: Optional[str] = Field(default="企业", max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None  # 备注（对应模型 notes 字段）


class CustomerCreate(CustomerBase):
    """客户创建 Schema"""
    pass


class CustomerUpdate(BaseModel):
    """客户更新 Schema"""
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    customer_type: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class CustomerInDB(CustomerBase):
    """客户数据库 Schema"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Customer(CustomerInDB):
    """客户响应 Schema"""
    project_count: int = 0
    total_amount: Optional[Decimal] = None
