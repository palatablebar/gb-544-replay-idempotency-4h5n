"""多职责格式化：时间戳、行数千分位、耗时、水位线文本、枚举中文名、cron 人类可读化。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.constants.enums import ENUM_LABELS

CRON_COMMON: dict[str, str] = {
    "0 2 * * *": "每天 02:00",
    "0 * * * *": "每小时整点",
    "*/15 * * * *": "每 15 分钟",
    "0 0 * * *": "每天 00:00",
}


def fmt_ts(value: datetime | str | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def fmt_count(value: int | None) -> str:
    if value is None:
        return "0"
    return f"{value:,}"


def fmt_duration(started: datetime | None, finished: datetime | None) -> str:
    if not started:
        return "—"
    end = finished or datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    seconds = max(int((end - started).total_seconds()), 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def enum_label(enum_name: str, value: str | None) -> str:
    if not value:
        return "—"
    return ENUM_LABELS.get(enum_name, {}).get(value, value)


def fmt_watermark(value: Any) -> str:
    if value in (None, ""):
        return "（初始）"
    return str(value)


def watermark_text(watermark_from: Any, watermark_value: Any) -> str:
    """时间线文案：把两次水位线格式化成『上一水位 → 本批水位』。"""
    frm = fmt_watermark(watermark_from)
    to = fmt_watermark(watermark_value)
    if frm == to:
        return f"水位线停在 {to}（本批无新数据）"
    return f"水位线 {frm} → {to}"


def is_no_new_data(rows_read: int, watermark_from: Any, watermark_value: Any) -> bool:
    return rows_read == 0 or str(watermark_from) == str(watermark_value)


def cron_text(expr: str | None) -> str:
    if not expr:
        return "未设置"
    if expr in CRON_COMMON:
        return CRON_COMMON[expr]
    return f"cron {expr}"


def fmt_rows_triplet(rows_read: int | None, rows_written: int | None, rows_rejected: int | None) -> str:
    return f"{fmt_count(rows_read)} / {fmt_count(rows_written)} / {fmt_count(rows_rejected)}"
