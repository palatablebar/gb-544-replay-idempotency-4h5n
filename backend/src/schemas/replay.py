"""重放批次序列化：运行详情页展示重放进度用。"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def serialize_replay_batch(batch: Any) -> dict[str, Any]:
    return {
        "id": str(batch.id),
        "run_id": str(batch.run_id),
        "status": batch.status,
        "total": batch.total,
        "processed": batch.cursor,
        "written": batch.written,
        "still_rejected": batch.still_rejected,
        "progress_text": f"{batch.cursor}/{batch.total}",
        "error_message": batch.error_message,
        "created_at": _iso(batch.created_at),
        "finished_at": _iso(batch.finished_at),
    }
