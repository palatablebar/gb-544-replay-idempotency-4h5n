"""JSONL 读取：每行一个 JSON 对象，键集合取并集作为字段清单。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.constants import error_codes as codes
from src.utils.errors import AppError


def _iter_lines(path: str | Path):
    if not Path(path).exists():
        raise AppError(codes.SOURCE_UNREACHABLE, "JSONL 文件不存在", f"path={path}")
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError as exc:
                raise AppError(
                    codes.SOURCE_UNREACHABLE, "JSONL 行解析失败", f"line={line_no} error={exc}"
                ) from exc


def probe_jsonl(path: str | Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    for _, obj in _iter_lines(path):
        if isinstance(obj, dict):
            rows.append(obj)
            for key in obj:
                if key not in columns:
                    columns.append(key)
        if len(rows) >= 2000:
            break
    return {
        "delimiter": None,
        "encoding": "utf-8",
        "has_header": True,
        "columns": columns,
        "row_count": len(rows),
        "sample": rows[:20],
    }


def read_jsonl_rows(path: str | Path, columns: list[str] | None = None) -> list[dict[str, Any]]:
    rows = []
    for _, obj in _iter_lines(path):
        if not isinstance(obj, dict):
            continue
        row = dict(obj)
        if columns:
            for column in columns:
                row.setdefault(column, "")
            row = {c: row.get(c, "") for c in columns}
        rows.append(row)
    return rows
