from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

SOURCE_TYPES = ("csv", "jsonl", "postgres_table", "mock_rest")


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    source_type: str
    config: dict[str, Any] = {}


class SourceUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None


class SourceConfigUpdate(BaseModel):
    config: dict[str, Any]


def serialize_source(source: Any, referenced_pipelines: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": str(source.id),
        "name": source.name,
        "source_type": source.source_type,
        "config": source.config_json or {},
        "status": source.status,
        "last_probed_at": source.last_probed_at.isoformat() if isinstance(source.last_probed_at, datetime) else None,
        "probe_result": source.probe_result_json or {},
        "owner_id": str(source.owner_id),
        "created_at": source.created_at.isoformat() if isinstance(source.created_at, datetime) else None,
        "referenced_pipelines": referenced_pipelines or [],
    }
