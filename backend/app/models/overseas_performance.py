"""海外管理绩效汇报配置与历史快照。"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class OverseasPerformanceConfig(Base):
    __tablename__ = "overseas_performance_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_overseas_performance_config_user"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="all_projects")
    schedule_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="quarterly")
    schedule_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schedule_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=9)
    schedule_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criteria_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User")


class OverseasPerformanceReport(Base):
    __tablename__ = "overseas_performance_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    period_label: Mapped[str] = mapped_column(String(100), nullable=False)
    period_type: Mapped[str] = mapped_column(String(30), nullable=False, default="custom")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="all_projects")
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="成功", index=True)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
