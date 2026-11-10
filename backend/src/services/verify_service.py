"""校验服务：管道保存前校验 + 运行后的行数账目校验。"""
from __future__ import annotations

from typing import Any

from src.constants import error_codes as codes
from src.constants.enums import SyncMode
from src.utils.errors import AppError


def validate_pipeline_config(
    *,
    pipeline_id: Any,
    sync_mode: str,
    watermark_column: str | None,
    conflict_strategy: str,
    conflict_key: str | None,
    target_schema: str,
    target_table: str,
    mappings: list[Any],
) -> None:
    entity = "SyncPipeline"
    if sync_mode == SyncMode.INCREMENTAL.value and not watermark_column:
        raise AppError(
            codes.WATERMARK_MISSING,
            "增量模式必须指定水位线列",
            f"{entity}[id={pipeline_id}] validate failed: incremental requires watermark_column",
        )
    if not conflict_key and conflict_strategy:
        raise AppError(
            codes.CONFLICT_KEY_ABSENT,
            "冲突策略生效但未配置冲突键",
            f"{entity}[id={pipeline_id}] validate failed: conflict_key required",
        )
    if not mappings:
        raise AppError(
            codes.PIPELINE_INVALID_MAPPING,
            "管道没有字段映射",
            f"{entity}[id={pipeline_id}] validate failed: mapping empty",
        )
    from src.services.load_service import reflect_table

    try:
        table = reflect_table(target_schema, target_table)
    except AppError:
        raise
    target_columns = set(table.c.keys())
    seen: set[str] = set()
    for mapping in mappings:
        column = mapping["target_column"] if isinstance(mapping, dict) else mapping.target_column
        if column in seen:
            raise AppError(
                codes.PIPELINE_INVALID_MAPPING,
                "目标列重复",
                f"{entity}[id={pipeline_id}] validate failed: duplicate target_column={column}",
            )
        seen.add(column)
        if column not in target_columns:
            raise AppError(
                codes.TARGET_TABLE_MISSING,
                "目标列不存在",
                f"{entity}[id={pipeline_id}] validate failed: column {column} missing "
                f"in {target_schema}.{target_table}",
            )
    if watermark_column and watermark_column not in _source_fields(mappings):
        raise AppError(
            codes.WATERMARK_MISSING,
            "水位线列未出现在映射的源字段中",
            f"{entity}[id={pipeline_id}] validate failed: watermark_column={watermark_column} not mapped",
        )


def _source_fields(mappings: list[Any]) -> set[str]:
    fields: set[str] = set()
    for mapping in mappings:
        if isinstance(mapping, dict):
            fields.add(mapping["source_field"])
        else:
            fields.add(mapping.source_field)
    return fields


def verify_totals(rows_read: int, written: int, skipped: int, rejected: int) -> dict[str, Any]:
    accounted = written + skipped + rejected
    return {
        "ok": accounted == rows_read,
        "rows_read": rows_read,
        "accounted": accounted,
        "delta": rows_read - accounted,
    }
