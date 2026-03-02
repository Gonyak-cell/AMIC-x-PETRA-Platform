"""deal-mgmt Celery 앱 팩토리.

Redis 브로커 기반 Celery 앱을 생성하고 구성한다.
JSON 직렬화만 허용하며, pickle은 보안상 금지한다.
"""

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
    # 직렬화: JSON만 허용 (pickle 금지)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 신뢰성
    task_acks_late=True,
    task_track_started=True,
    # 리소스 제한
    worker_max_memory_per_child=500_000,
    # 타임아웃
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_hard_time_limit=settings.CELERY_TASK_HARD_TIME_LIMIT,
    # 결과 만료 (24시간)
    result_expires=86400,
)

# ── Celery Beat 스케줄 ──────────────────────────────────

celery_app.conf.beat_schedule = {
    "cleanup-orphan-blobs-daily": {
        "task": "deal_mgmt.cleanup_orphan_blobs",
        "schedule": crontab(hour=3, minute=0),
    },
}

celery_app.autodiscover_tasks(["app.tasks"])
