"""四类源统一抽取接口：按 SourceType 选择连接器。"""
from __future__ import annotations

from typing import Any

from src.constants import error_codes as codes
from src.constants.enums import SourceType
from src.utils.errors import AppError
from worker_src.connectors import csv_connector, jsonl_connector, postgres_connector, rest_connector

CONNECTORS = {
    SourceType.CSV.value: csv_connector,
    SourceType.JSONL.value: jsonl_connector,
    SourceType.POSTGRES_TABLE.value: postgres_connector,
    SourceType.MOCK_REST.value: rest_connector,
}


def read_rows(source_type: str, config: dict[str, Any], columns: list[str] | None = None) -> list[dict[str, Any]]:
    connector = CONNECTORS.get(source_type)
    if connector is None:
        raise AppError(codes.SOURCE_UNREACHABLE, "未知数据源类型", f"source_type={source_type}")
    if source_type == SourceType.MOCK_REST.value:
        return connector.read(config, columns)
    return connector.read(config, columns=columns)
