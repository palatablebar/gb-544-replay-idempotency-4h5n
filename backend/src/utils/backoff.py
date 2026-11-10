"""指数退避 + 抖动，上限 5 次。"""
from __future__ import annotations

import random

from src.constants.limits import MAX_RETRY_ATTEMPTS


def compute_delay(retry_count: int, base: float = 1.0, cap: float = 30.0) -> float:
    exp = base * (2 ** max(retry_count - 1, 0))
    jitter = random.uniform(0, 0.4) * exp
    return round(min(exp + jitter, cap), 2)


def should_retry(retry_count: int, max_attempts: int = MAX_RETRY_ATTEMPTS) -> bool:
    return retry_count < max_attempts
