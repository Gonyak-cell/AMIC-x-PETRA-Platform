"""마케팅 자료 PPTX 생성 백그라운드 태스크 — Celery 래퍼."""

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
    name="deal_mgmt.marketing.generate_pptx",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    acks_late=True,
)
def generate_pptx_task(
    self,
    mat_id: str,
    transaction_id: str,
    body_dict: dict,
) -> None:
    """마케팅 자료(TM/DM/IM) PPTX 생성."""
    from celery.exceptions import SoftTimeLimitExceeded

    from app.core.database import async_session_factory
    from app.schemas.marketing_material import MarketingMaterialCreate
    from app.services.marketing_material_service import _generate_pptx

    logger.info("Celery: PPTX 생성 시작 (mat=%s, txn=%s)", mat_id, transaction_id)

    body = MarketingMaterialCreate.model_validate(body_dict)
    try:
        _run_async(
            _generate_pptx(
                mat_id=uuid.UUID(mat_id),
                transaction_id=uuid.UUID(transaction_id),
                body=body,
                session_factory=async_session_factory,
            )
        )
    except SoftTimeLimitExceeded:
        logger.warning("PPTX 생성 soft_time_limit 초과 (mat=%s)", mat_id)
    except Exception:
        logger.exception("PPTX 생성 실패 (mat=%s)", mat_id)
        raise self.retry(countdown=60)
