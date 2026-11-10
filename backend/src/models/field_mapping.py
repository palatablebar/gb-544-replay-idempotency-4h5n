from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, new_uuid, utcnow


class FieldMapping(Base):
    __tablename__ = "field_mappings"
    __table_args__ = {"schema": settings.meta_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.meta_schema}.sync_pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_field: Mapped[str] = mapped_column(String(120), nullable=False)
    target_column: Mapped[str] = mapped_column(String(120), nullable=False)
    transform_type: Mapped[str] = mapped_column(String(30), nullable=False, default="trim")
    transform_config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    default_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
