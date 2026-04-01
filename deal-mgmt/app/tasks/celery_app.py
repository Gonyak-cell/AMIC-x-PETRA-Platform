from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "deal_mgmt",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_track_started=True,
    worker_max_memory_per_child=500_000,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_hard_time_limit=settings.CELERY_TASK_HARD_TIME_LIMIT,
    result_expires=86400,
)

celery_app.conf.beat_schedule = {
    "cleanup-orphan-blobs-daily": {
        "task": "deal_mgmt.cleanup_orphan_blobs",
        "schedule": crontab(hour=3, minute=0),
    },
    "requeue-pending-attachment-processing": {
        "task": "deal_mgmt.attachments.requeue_pending",
        "schedule": crontab(minute="*/10"),
    },
    "collect-cf-news-hourly": {
        "task": "deal_mgmt.news.collect_cf_sources",
        "schedule": crontab(minute=0),
    },
}

celery_app.autodiscover_tasks(["app.tasks"])
