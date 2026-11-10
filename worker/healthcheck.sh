#!/bin/sh
# worker 健康检查：先 celery inspect ping，再兜底 Redis 心跳键（beat 写入）。
cd /app || exit 1
python - <<'PY'
import os
import sys
import time

os.environ.setdefault("PYTHONPATH", "/app:/app/backend")

import redis  # noqa: E402

URl = os.environ.get("REDIS_URL", "redis://redis:6379/0")

def heartbeat_ok() -> bool:
    try:
        client = redis.Redis.from_url(URl, decode_responses=True)
        value = client.get("syncmesh:worker:heartbeat")
        if not value:
            return False
        return (time.time() - float(value)) < 90
    except Exception:
        return False

def celery_ok() -> bool:
    try:
        from worker_src.config.celery_app import celery_app

        replies = celery_app.control.ping(timeout=3)
        return bool(replies)
    except Exception:
        return False

if heartbeat_ok() or celery_ok():
    print("worker healthy")
    sys.exit(0)
print("worker unhealthy: no heartbeat and no celery pong")
sys.exit(1)
PY
