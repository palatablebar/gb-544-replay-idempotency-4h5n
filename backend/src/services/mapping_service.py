"""字段映射服务：读取、批量保存、试运行（before/after）、必填与目标列重复校验。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import TransformType
from src.constants.messages import MSG_MAPPING_EMPTY_TARGET, MSG_MAPPING_REQUIRED
from src.models.field_mapping import FieldMapping
from src.models.sync_pipeline import SyncPipeline
from src.schemas.mapping import MappingItem, serialize_mapping
from src.services import extract_service, transform_service
from src.utils.errors import AppError


def _pipeline_mappings(db: Session, pipeline_id: Any) -> list[FieldMapping]:
    return (
        db.query(FieldMapping)
        .filter(FieldMapping.pipeline_id == pipeline_id)
        .order_by(FieldMapping.order_index.asc(), FieldMapping.created_at.asc())
        .all()
    )


def list_mappings(db: Session, pipeline_id: Any) -> list[dict[str, Any]]:
    return [serialize_mapping(mapping) for mapping in _pipeline_mappings(db, pipeline_id)]


def mapping_dicts(db: Session, pipeline_id: Any) -> list[dict[str, Any]]:
    """worker / 转换阶段使用的纯字典形态（按 order_index 排序）。"""
    mappings = _pipeline_mappings(db, pipeline_id)
    return [
        {
            "source_field": mapping.source_field,
            "target_column": mapping.target_column,
            "transform_type": mapping.transform_type,
            "transform_config": mapping.transform_config_json or {},
            "default_value": mapping.default_value,
            "is_required": mapping.is_required,
            "order_index": mapping.order_index,
        }
        for mapping in mappings
    ]


def _validate_items(items: list[MappingItem]) -> list[dict[str, Any]]:
    if not items:
        raise AppError(codes.PIPELINE_INVALID_MAPPING, MSG_MAPPING_REQUIRED, "mappings empty")
    payload: list[dict[str, Any]] = []
    seen_columns: set[str] = set()
    for index, item in enumerate(items):
        target_column = (item.target_column or "").strip()
        if not target_column:
            raise AppError(
                codes.PIPELINE_INVALID_MAPPING, MSG_MAPPING_EMPTY_TARGET, f"row#{index} target_column empty"
            )
        if target_column in seen_columns:
            raise AppError(
                codes.PIPELINE_INVALID_MAPPING,
                f"目标列重复：{target_column}",
                f"duplicate target_column={target_column}",
            )
        seen_columns.add(target_column)
        try:
            config = transform_service.validate_mapping_config(
                item.transform_type or TransformType.TRIM.value, item.transform_config
            )
        except transform_service.TransformFailure as failure:
            raise AppError(
                codes.PIPELINE_INVALID_MAPPING,
                f"{target_column} 的转换参数不合法",
                failure.detail,
            ) from failure
        payload.append(
            {
                "source_field": (item.source_field or "").strip(),
                "target_column": target_column,
                "transform_type": item.transform_type or TransformType.TRIM.value,
                "transform_config": config,
                "default_value": item.default_value,
                "is_required": bool(item.is_required),
                "order_index": item.order_index if item.order_index is not None else index,
            }
        )
    return payload


def save_mappings(db: Session, pipeline: SyncPipeline, items: list[MappingItem]) -> list[dict[str, Any]]:
    payload = _validate_items(items)
    db.query(FieldMapping).filter(FieldMapping.pipeline_id == pipeline.id).delete()
    for item in payload:
        db.add(
            FieldMapping(
                pipeline_id=pipeline.id,
                source_field=item["source_field"],
                target_column=item["target_column"],
                transform_type=item["transform_type"],
                transform_config_json=item["transform_config"],
                default_value=item["default_value"],
                is_required=item["is_required"],
                order_index=item["order_index"],
            )
        )
    db.commit()
    return list_mappings(db, pipeline.id)


def fill_from_probe(source_columns: list[str], target_columns: list[str]) -> list[dict[str, Any]]:
    """从源字段清单一键填充：同名优先，其次按位置配对。"""
    rows: list[dict[str, Any]] = []
    remaining_targets = [
        column for column in target_columns if not column.startswith("_")
    ]
    for index, column in enumerate(source_columns):
        if column in remaining_targets:
            target = column
            remaining_targets.remove(column)
        elif remaining_targets:
            target = remaining_targets.pop(0)
        else:
            target = column
        rows.append(
            {
                "source_field": column,
                "target_column": target,
                "transform_type": TransformType.TRIM.value,
                "transform_config": {},
                "default_value": None,
                "is_required": False,
                "order_index": index,
            }
        )
    return rows


def preview(db: Session, pipeline: SyncPipeline, items: list[MappingItem] | None, limit: int = 20) -> dict[str, Any]:
    from src.models.data_source import DataSource

    source = db.get(DataSource, pipeline.source_id)
    if source is None:
        raise AppError(codes.NOT_FOUND, "数据源不存在", f"source_id={pipeline.source_id}")
    if items:
        mapping_payload = _validate_items(items)
    else:
        mapping_payload = mapping_dicts(db, pipeline.id)
    if not mapping_payload:
        raise AppError(codes.PIPELINE_INVALID_MAPPING, MSG_MAPPING_REQUIRED, "no mapping to preview")

    probe = source.probe_result_json or {}
    source_columns = probe.get("columns") or [
        item["source_field"] for item in mapping_payload
    ]
    rows = extract_service.read_source_rows(
        source.source_type, source.config_json or {}, columns=source_columns
    )
    samples: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, row in enumerate(rows[:limit]):
        mapped, row_failures = transform_service.transform_row(row, mapping_payload, index)
        samples.append({"index": index, "before": row, "after": mapped})
        failures.extend(row_failures)
    return {
        "mappings": mapping_payload,
        "samples": samples,
        "failures": failures[:20],
        "columns": source_columns,
    }


def mapping_snapshot(db: Session, pipeline_id: Any) -> list[dict[str, Any]]:
    return mapping_dicts(db, pipeline_id)
