"""worker Celery 应用：消费 backend 投递的同名任务，并跑 beat 扫描 cron。"""
from __future__ import annotations

from celery import Celery
from celery.schedules import schedule

from worker_src.config.settings import settings
from worker_src.constants.tuning import REPLAY_RESUME_SCAN_SECONDS

celery_app = Celery(
    "syncmesh_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "worker_src.tasks.sync_task",
        "worker_src.tasks.schedule_task",
        "worker_src.tasks.replay_task",
        "worker_src.tasks.replay_resume_task",
        "worker_src.tasks.cleanup_task",
        "worker_src.tasks.heartbeat_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=False,
)

celery_app.conf.beat_schedule = {
    "scan-cron-pipelines": {
        "task": "syncmesh.scan_schedules",
        "schedule": schedule(run_every=settings.scheduler_poll_seconds),
    },
    "worker-heartbeat": {
        "task": "syncmesh.heartbeat",
        "schedule": schedule(run_every=10),
    },
    "resume-stale-replays": {
        "task": "syncmesh.resume_replays",
        "schedule": schedule(run_every=REPLAY_RESUME_SCAN_SECONDS),
    },
    "cleanup-staging": {
        "task": "syncmesh.cleanup_staging",
        "schedule": schedule(run_every=1800),
    },
}
