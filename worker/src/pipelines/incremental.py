"""增量过滤与水位线推进：真实比较 watermark_column。"""
from __future__ import annotations

from typing import Any

from src.utils.watermark import compare, max_watermark, should_advance


def watermark_from(configured: Any, target_max: Any) -> Any:
    if configured not in (None, ""):
        return configured
    return target_max


def filter_rows(
    rows: list[dict[str, Any]],
    *,
    sync_mode: str,
    watermark_column: str | None,
    watermark: Any,
) -> tuple[list[dict[str, Any]], int, Any]:
    """返回 (本批行, 被水位线过滤掉的行数, 本批最大水位线)。"""
    if sync_mode != "incremental" or not watermark_column:
        values = [row.get(watermark_column) for row in rows] if watermark_column else []
        return rows, 0, max_watermark(values) if watermark_column else None
    kept: list[dict[str, Any]] = []
    filtered = 0
    for row in rows:
        value = row.get(watermark_column)
        if should_advance(value, watermark):
            kept.append(row)
        else:
            filtered += 1
    next_watermark = max_watermark([row.get(watermark_column) for row in kept], watermark)
    return kept, filtered, next_watermark


def describe(watermark: Any, next_watermark: Any) -> str:
    from src.utils.formatters import watermark_text

    return watermark_text(watermark, next_watermark)


def is_later(left: Any, right: Any) -> bool:
    return compare(left, right) > 0
