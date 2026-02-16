"""Celery 앱 팩토리 (T-I11).

> 마지막 수정: 2026-02-10 17:39:59

Redis 브로커 기반 Celery 앱을 생성하고 구성한다.
JSON 직렬화만 허용하며, pickle은 보안상 금지한다.
"""

from __future__ import annotations

from celery import Celery

from src.api.config import APIConfig, get_config


def create_celery_app(config: APIConfig | None = None) -> Celery:
    """Celery 앱을 생성하고 설정을 적용한다.

    Args:
        config: API 설정. None이면 get_config() 사용.

    Returns:
        구성된 Celery 인스턴스.
    """
    cfg = config or get_config()

    app = Celery(
        "im_generator",
        broker=cfg.redis_url,
        backend=cfg.redis_result_backend,
    )

    app.conf.update(
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
        task_soft_time_limit=cfg.celery_task_soft_time_limit,
        task_hard_time_limit=cfg.celery_task_hard_time_limit,
        # 결과 만료 (24시간)
        result_expires=86400,
    )

    app.autodiscover_tasks(["src.api.tasks"])

    return app


celery_app = create_celery_app()
