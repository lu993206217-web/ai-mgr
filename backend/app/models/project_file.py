"""
项目文件模型

记录项目相关资料的索引信息，例如售前交流、商务、合同、技术方案等文件。
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ProjectFile(Base):
    """项目文件索引表模型"""

    __tablename__ = "project_files"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)

    file_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_category: Mapped[str] = mapped_column(String(50), nullable=False, default="其他", index=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    owner_party: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    project = relationship("Project", back_populates="files")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<ProjectFile {self.file_name}>"
