"""Redis 客户端（限流桶、管道锁短期状态、Mock REST 状态开关）。"""
from __future__ import annotations

from functools import lru_cache

import redis

from src.config.settings import settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def redis_ping() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
