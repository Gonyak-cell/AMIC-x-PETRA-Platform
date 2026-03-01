"""문서 AI 추출 백그라운드 태스크 — Celery 래퍼."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import uuid

from celery.exceptions import SoftTimeLimitExceeded

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Celery 워커에서 코루틴을 안전하게 실행한다."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()


@celery_app.task(
    name="deal_mgmt.extraction.run_pipeline",
    bind=True,
    soft_time_limit=300,  # 5분
    acks_late=True,  # 워커 크래시 시 메시지 재전달 (명시적 self.retry 미사용)
)
def run_extraction_task(self, extraction_id: str) -> None:
    """VDR 문서 AI 추출 파이프라인을 실행한다."""
    from app.core.database import async_session_factory
    from app.services.document_extraction_service import run_extraction_pipeline

    logger.info("Celery: 문서 추출 시작 (extraction=%s)", extraction_id)

    try:
        _run_async(
            run_extraction_pipeline(
                extraction_id=uuid.UUID(extraction_id),
                session_factory=async_session_factory,
            )
        )
    except SoftTimeLimitExceeded:
        logger.warning("Celery: soft_time_limit 초과 (extraction=%s)", extraction_id)
        from app.services.document_extraction_service import mark_extraction_failed

        _run_async(
            mark_extraction_failed(
                async_session_factory,
                uuid.UUID(extraction_id),
                "AI 분석 시간이 초과되었습니다. 다시 시도해주세요.",
            )
        )
    except Exception:
        logger.exception("Celery: 문서 추출 실패 (extraction=%s)", extraction_id)
        raise
