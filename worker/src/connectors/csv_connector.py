"""CSV 连接器：复用 backend utils/csv_reader 的解析逻辑。"""
from __future__ import annotations

from typing import Any

from src.services import extract_service


def probe(config: dict[str, Any]) -> dict[str, Any]:
    return extract_service.probe_source("csv", config)


def read(config: dict[str, Any], columns: list[str] | None = None) -> list[dict[str, Any]]:
    return extract_service.read_source_rows("csv", config, columns=columns)
