"""拒绝原因码（与 backend/constants/enums.py 的 ReasonCode 一致）。"""
from __future__ import annotations

REASON_REQUIRED_MISSING = "required_missing"
REASON_TYPE_MISMATCH = "type_mismatch"
REASON_TRANSFORM_FAILED = "transform_failed"
REASON_CONFLICT_REJECTED = "conflict_rejected"
REASON_CONSTRAINT_VIOLATION = "constraint_violation"

ALL_REASON_CODES = [
    REASON_REQUIRED_MISSING,
    REASON_TYPE_MISMATCH,
    REASON_TRANSFORM_FAILED,
    REASON_CONFLICT_REJECTED,
    REASON_CONSTRAINT_VIOLATION,
]

REASON_LABELS = {
    REASON_REQUIRED_MISSING: "必填字段缺失",
    REASON_TYPE_MISMATCH: "类型不匹配",
    REASON_TRANSFORM_FAILED: "转换失败",
    REASON_CONFLICT_REJECTED: "冲突被拒绝",
    REASON_CONSTRAINT_VIOLATION: "约束冲突",
}
