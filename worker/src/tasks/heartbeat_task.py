"""worker 心跳：写 Redis 键给 healthcheck 兜底判定（beat 每 10s 一次）。"""
from __future__ import annotations

import time

import redis

from worker_src.config.celery_app import celery_app
from worker_src.config.settings import settings

HEARTBEAT_KEY = "syncmesh:worker:heartbeat"


@celery_app.task(name="syncmesh.heartbeat")
def heartbeat() -> float:
    now = time.time()
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.set(HEARTBEAT_KEY, str(now), ex=120)
    except Exception:  # noqa: BLE001
        pass
    return now
