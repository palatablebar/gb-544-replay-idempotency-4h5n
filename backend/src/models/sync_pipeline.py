from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, new_uuid, utcnow


class SyncPipeline(Base):
    __tablename__ = "sync_pipelines"
    __table_args__ = {"schema": settings.meta_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.meta_schema}.users.id"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.meta_schema}.data_sources.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    target_schema: Mapped[str] = mapped_column(String(30), nullable=False, default="target")
    target_table: Mapped[str] = mapped_column(String(120), nullable=False)
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="incremental")
    watermark_column: Mapped[str | None] = mapped_column(String(120), nullable=True)
    conflict_strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="skip")
    conflict_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    schedule_cron: Mapped[str | None] = mapped_column(String(60), nullable=True)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    last_watermark: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=func.now(), nullable=False
    )
