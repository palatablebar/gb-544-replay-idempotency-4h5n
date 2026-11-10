from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MappingItem(BaseModel):
    id: str | None = None
    source_field: str = Field(min_length=1, max_length=120)
    target_column: str = Field(min_length=1, max_length=120)
    transform_type: str = "trim"
    transform_config: dict[str, Any] = {}
    default_value: str | None = None
    is_required: bool = False
    order_index: int = 0


class MappingBulkSave(BaseModel):
    mappings: list[MappingItem]


class MappingPreviewRequest(BaseModel):
    mappings: list[MappingItem] | None = None
    limit: int = Field(default=20, ge=1, le=20)


def serialize_mapping(mapping: Any) -> dict[str, Any]:
    return {
        "id": str(mapping.id),
        "pipeline_id": str(mapping.pipeline_id),
        "source_field": mapping.source_field,
        "target_column": mapping.target_column,
        "transform_type": mapping.transform_type,
        "transform_config": mapping.transform_config_json or {},
        "default_value": mapping.default_value,
        "is_required": mapping.is_required,
        "order_index": mapping.order_index,
    }
