from __future__ import annotations

from datetime import datetime
from typing import Any


def serialize_rejected(record: Any) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "run_id": str(record.run_id),
        "pipeline_id": str(record.pipeline_id),
        "raw_payload": record.raw_payload_json or {},
        "reason_code": record.reason_code,
        "reason_detail": record.reason_detail,
        "source_row_index": record.source_row_index,
        "replayed_at": record.replayed_at.isoformat() if isinstance(record.replayed_at, datetime) else None,
        "created_at": record.created_at.isoformat() if isinstance(record.created_at, datetime) else None,
    }
