from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TriggerRequest(BaseModel):
    pipeline_id: str
    trigger_type: str = "manual"


class ReplayRequest(BaseModel):
    rejected_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None


class RunQuery(BaseModel):
    status: str | None = None
    pipeline_id: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def serialize_run(run: Any, *, pipeline_name: str | None = None, source_type: str | None = None) -> dict[str, Any]:
    from src.utils.formatters import fmt_duration, fmt_rows_triplet, watermark_text

    return {
        "id": str(run.id),
        "pipeline_id": str(run.pipeline_id),
        "pipeline_name": pipeline_name,
        "source_type": source_type,
        "trigger_type": run.trigger_type,
        "triggered_by": str(run.triggered_by) if run.triggered_by else None,
        "actor_kind": run.actor_kind,
        "status": run.status,
        "rows_read": run.rows_read,
        "rows_written": run.rows_written,
        "rows_rejected": run.rows_rejected,
        "rows_skipped": run.rows_skipped,
        "rows_triplet": fmt_rows_triplet(run.rows_read, run.rows_written, run.rows_rejected),
        "watermark_from": run.watermark_from,
        "watermark_value": run.watermark_value,
        "watermark_text": watermark_text(run.watermark_from, run.watermark_value),
        "stage": run.stage,
        "stage_history": run.stage_history or [],
        "error_message": run.error_message,
        "error_code": run.error_code,
        "retry_count": run.retry_count,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "created_at": _iso(run.created_at),
        "duration_text": fmt_duration(run.started_at, run.finished_at),
    }
