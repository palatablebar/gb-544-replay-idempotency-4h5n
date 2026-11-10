"""水位线比较：支持时间戳 / 自增 ID / 字符串三种形态。"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def coerce(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if text == "":
        return None
    if text.isdigit():
        return int(text)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[: len(fmt) + 4], fmt)
        except ValueError:
            continue
    return text


def compare(value: Any, watermark: Any) -> int:
    """返回 -1/0/1；None 视为最小。"""
    left, right = coerce(value), coerce(watermark)
    if left is None and right is None:
        return 0
    if left is None:
        return -1
    if right is None:
        return 1
    try:
        if left == right:
            return 0
        return 1 if left > right else -1
    except TypeError:
        return 1 if str(left) > str(right) else -1


def should_advance(value: Any, watermark: Any) -> bool:
    return compare(value, watermark) > 0


def max_watermark(values: list[Any], current: Any = None) -> Any:
    best = current
    for value in values:
        if should_advance(value, best):
            best = value
    return best
