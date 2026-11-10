"""退避策略：按 retry_count 决定是否重新入队。"""
from __future__ import annotations

from src.constants import error_codes as codes
from src.utils.backoff import compute_delay
from worker_src.constants.tuning import RETRY_MAX_ATTEMPTS

TRANSIENT_CODES = {
    codes.SOURCE_UNREACHABLE,
    codes.INTERNAL_ERROR,
    codes.MOCK_REST_RATE_LIMITED,
}


def should_retry(retry_count: int, error_code: str | None) -> bool:
    if error_code and error_code not in TRANSIENT_CODES:
        return False
    return retry_count < RETRY_MAX_ATTEMPTS


def next_delay(retry_count: int) -> float:
    return compute_delay(retry_count)
