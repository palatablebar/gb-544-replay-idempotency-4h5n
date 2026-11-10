"""按映射逐列转换（批次推进，产出拒绝项）。"""
from __future__ import annotations

from typing import Any

from src.services import transform_service
from src.utils.logger import get_logger

logger = get_logger("syncmesh.worker.transform")


def transform_batch(
    rows: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    *,
    start_index: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mapped_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for offset, row in enumerate(rows):
        source_row_index = start_index + offset
        mapped, row_failures = transform_service.transform_row(row, mappings, source_row_index)
        if row_failures:
            # 一行中任一映射失败整行拒绝，原始载荷完整保留以便重放
            for failure in row_failures:
                failure["source_row_index"] = source_row_index
            failures.extend(row_failures)
            continue
        mapped["__raw_payload__"] = row
        mapped["__source_row_index__"] = source_row_index
        mapped_records.append(mapped)
    logger.info(
        "transform batch rows=%s mapped=%s rejected=%s",
        len(rows),
        len(mapped_records),
        len(failures),
    )
    return mapped_records, failures


def transform_one(row: dict[str, Any], mappings: list[dict[str, Any]], source_row_index: int = 0):
    mapped, failures = transform_service.transform_row(row, mappings, source_row_index)
    if failures:
        for failure in failures:
            failure["source_row_index"] = source_row_index
        return None, failures
    mapped["__raw_payload__"] = row
    mapped["__source_row_index__"] = source_row_index
    return mapped, []
