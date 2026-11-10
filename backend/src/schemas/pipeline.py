from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    source_id: str
    target_table: str = Field(min_length=1, max_length=120)
    data_schema: str = Field(default="target", alias="target_schema")
    sync_mode: str = "incremental"
    watermark_column: str | None = None
    conflict_strategy: str = "skip"
    conflict_key: str | None = None
    schedule_cron: str | None = None
    batch_size: int = Field(default=100, ge=1, le=2000)

    model_config = {"populate_by_name": True}


class PipelineUpdate(BaseModel):
    name: str | None = None
    target_table: str | None = None
    data_schema: str | None = Field(default=None, alias="target_schema")
    sync_mode: str | None = None
    watermark_column: str | None = None
    conflict_strategy: str | None = None
    conflict_key: str | None = None
    schedule_cron: str | None = None
    batch_size: int | None = Field(default=None, ge=1, le=2000)

    model_config = {"populate_by_name": True}


def serialize_pipeline(
    pipeline: Any,
    *,
    source_name: str | None = None,
    source_type: str | None = None,
    source_status: str | None = None,
    last_run: dict[str, Any] | None = None,
    mapping_count: int = 0,
) -> dict[str, Any]:
    return {
        "id": str(pipeline.id),
        "name": pipeline.name,
        "owner_id": str(pipeline.owner_id),
        "source_id": str(pipeline.source_id),
        "source_name": source_name,
        "source_type": source_type,
        "source_status": source_status,
        "target_schema": pipeline.target_schema,
        "target_table": pipeline.target_table,
        "target_full_name": f"{pipeline.target_schema}.{pipeline.target_table}",
        "sync_mode": pipeline.sync_mode,
        "watermark_column": pipeline.watermark_column,
        "conflict_strategy": pipeline.conflict_strategy,
        "conflict_key": pipeline.conflict_key,
        "schedule_cron": pipeline.schedule_cron,
        "batch_size": pipeline.batch_size,
        "status": pipeline.status,
        "last_watermark": pipeline.last_watermark,
        "mapping_count": mapping_count,
        "created_at": pipeline.created_at.isoformat() if isinstance(pipeline.created_at, datetime) else None,
        "updated_at": pipeline.updated_at.isoformat() if isinstance(pipeline.updated_at, datetime) else None,
        "last_run": last_run,
    }
