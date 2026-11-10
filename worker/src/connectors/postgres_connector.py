"""PostgreSQL 表连接器：同一实例不同 schema。"""
from __future__ import annotations

from typing import Any

from src.services import extract_service


def read(config: dict[str, Any], columns: list[str] | None = None) -> list[dict[str, Any]]:
    return extract_service.read_source_rows("postgres_table", config, columns=columns)
