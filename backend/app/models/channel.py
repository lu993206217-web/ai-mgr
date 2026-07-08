"""
渠道模型

渠道主档案（Channel Master）。
"""
from datetime import datetime, date
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import String, Date, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import ChannelCooperationStatus


class Channel(Base):
    """渠道表模型"""
    
    __tablename__ = "channels"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    channel_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cooperation_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="普通")
    cooperation_status: Mapped[ChannelCooperationStatus] = mapped_column(nullable=False, default=ChannelCooperationStatus.ACTIVE)
    cooperation_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # 统计字段（冗余，从关联表计算）
    total_project_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_deal_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(15, 2), nullable=True, default=0)
    bid_win_rate: Mapped[Optional[Numeric]] = mapped_column(Numeric(5, 2), nullable=True, default=0)
    last_contact_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # 关系
    projects = relationship("Project", back_populates="channel")
    
    def __repr__(self) -> str:
        return f"<Channel {self.channel_name}>"
