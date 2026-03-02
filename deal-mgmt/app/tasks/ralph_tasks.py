"""Ralph Loop 세션 백그라운드 태스크 — Celery 래퍼."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import uuid
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Celery 워커에서 코루틴을 안전하게 실행한다."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()


@celery_app.task(
    name="deal_mgmt.ralph.run_loop",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,
    acks_late=True,
)
def run_ralph_loop_task(
    self,
    session_id: str,
    body_dict: dict,
) -> None:
    """Ralph Loop 세션을 실행한다."""
    from celery.exceptions import SoftTimeLimitExceeded

    from app.routers.ralph import _run_ralph_loop
    from app.schemas.ralph import RalphSessionCreate

    logger.info("Celery: Ralph Loop 시작 (session=%s)", session_id)

    body = RalphSessionCreate.model_validate(body_dict)
    try:
        _run_async(
            _run_ralph_loop(
                session_id=uuid.UUID(session_id),
                body=body,
            )
        )
    except SoftTimeLimitExceeded:
        logger.warning("Ralph Loop soft_time_limit 초과 (session=%s)", session_id)
    except Exception:
        logger.exception("Ralph Loop 실패 (session=%s)", session_id)
        raise self.retry(countdown=60)
