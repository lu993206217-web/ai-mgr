"""
报价模型

软件报价单 - 包含软件授权明细和实施服务。
支持多产品、多授权类型、多服务项的复杂报价结构。
"""
import json
from datetime import datetime, date
from typing import Optional
from uuid import uuid4, UUID
from decimal import Decimal

from sqlalchemy import String, DateTime, Date, Numeric, Text, ForeignKey, TypeDecorator, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class DecimalJSON(TypeDecorator):
    """支持 Decimal 的 JSON 列类型，自动将 Decimal 转为 float 存储"""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, cls=DecimalJSONEncoder)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class DecimalJSONEncoder(json.JSONEncoder):
    """支持 Decimal 类型的 JSON 编码器"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class Quote(Base):
    """软件报价单表模型"""

    __tablename__ = "quotes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # 关联字段
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    project_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    channel_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("channels.id"), nullable=True, index=True)

    # 报价单基本信息
    quote_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    quote_title: Mapped[str] = mapped_column(String(300), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="草稿", index=True)

    # ===== 软件授权明细（JSON 数组）=====
    license_items: Mapped[list] = mapped_column(DecimalJSON, nullable=False, default=list)
    license_subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))

    # ===== 实施服务明细（JSON 数组）=====
    service_items: Mapped[list] = mapped_column(DecimalJSON, nullable=False, default=list)
    service_subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))

    # ===== 汇总信息 ======
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))

    # 负责人
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # 附件和备注
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # 关系
    project = relationship("Project", back_populates="quotes")
    customer = relationship("Customer")
    owner = relationship("User", foreign_keys=[owner_id])

    def __repr__(self) -> str:
        return f"<Quote {self.quote_no}: {self.quote_title}>"
