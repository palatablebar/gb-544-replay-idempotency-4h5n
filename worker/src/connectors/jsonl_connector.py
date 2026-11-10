"""JSONL 连接器：复用 backend utils/jsonl_reader。"""
from __future__ import annotations

from typing import Any

from src.services import extract_service


def read(config: dict[str, Any], columns: list[str] | None = None) -> list[dict[str, Any]]:
    return extract_service.read_source_rows("jsonl", config, columns=columns)
