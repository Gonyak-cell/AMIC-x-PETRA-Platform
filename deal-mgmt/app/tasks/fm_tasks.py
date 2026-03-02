"""Financial Model 백그라운드 태스크 — Celery 래퍼.

기존 async 함수를 Celery 태스크로 래핑하여 실행한다.
async 함수의 로직은 변경하지 않고 _run_async()로 안전하게 실행.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import uuid
from typing import Any

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# 싱글턴 ThreadPoolExecutor — Celery 워커 수명 동안 재사용
_FALLBACK_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)


def _run_async(coro: Any) -> Any:
    """Celery 워커에서 코루틴을 안전하게 실행한다."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return _FALLBACK_POOL.submit(asyncio.run, coro).result()


def _rollback_fm_to_failed(fm_id: str, transaction_id: str, error_msg: str) -> None:
    """FM 상태를 FAILED로 롤백한다 (Celery 워커에서 호출)."""

    async def _update() -> None:
        from app.core.database import async_session_factory
        from app.models.enums import FinancialModelStatus
        from app.services.financial_model_service import get_financial_model

        async with async_session_factory() as db:
            fm = await get_financial_model(db, uuid.UUID(fm_id), uuid.UUID(transaction_id))
            if fm.status in (
                FinancialModelStatus.GENERATING,
                FinancialModelStatus.FINALIZING,
            ):
                fm.status = FinancialModelStatus.FAILED
                fm.error_message = error_msg[:500]
                await db.commit()

    try:
        _run_async(_update())
    except Exception:
        logger.error("FM %s 상태 FAILED 롤백 실패", fm_id, exc_info=True)


@celery_app.task(
    name="deal_mgmt.fm.vdr_extraction_and_ralph",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,
    acks_late=True,
)
def run_vdr_extraction_and_ralph_task(
    self,
    fm_id: str,
    transaction_id: str,
    vdr_document_ids: list[str],
    model_type: str,
    ralph_max_iterations: int = 2,
    ralph_max_cost_usd: float = 15.0,  # NOTE: Celery 직렬화 경계이므로 float 유지, 내부에서 Decimal 변환
) -> None:
    """FM Ralph Loop Pass 1 — VDR 추출 + 초안 Excel 생성."""
    from celery.exceptions import SoftTimeLimitExceeded

    from app.services.financial_model_service import _run_vdr_extraction_and_ralph

    logger.info(
        "Celery: FM Ralph Pass 1 시작 (fm=%s, txn=%s)",
        fm_id,
        transaction_id,
    )
    try:
        _run_async(
            _run_vdr_extraction_and_ralph(
                fm_id=uuid.UUID(fm_id),
                transaction_id=uuid.UUID(transaction_id),
                vdr_document_ids=vdr_document_ids,
                model_type=model_type,
                ralph_max_iterations=ralph_max_iterations,
                ralph_max_cost_usd=ralph_max_cost_usd,
            )
        )
    except SoftTimeLimitExceeded:
        logger.warning("FM Ralph Pass 1 soft_time_limit 초과 (fm=%s)", fm_id)
        _rollback_fm_to_failed(fm_id, transaction_id, "작업 시간 초과 (soft_time_limit)")
    except Exception:
        logger.exception("FM Ralph Pass 1 실패 (fm=%s)", fm_id)
        try:
            raise self.retry(countdown=60)
        except self.MaxRetriesExceededError:
            _rollback_fm_to_failed(fm_id, transaction_id, "최대 재시도 초과")
            raise


@celery_app.task(
    name="deal_mgmt.fm.finalize_and_generate",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,
    acks_late=True,
)
def run_finalize_and_generate_task(
    self,
    fm_id: str,
    transaction_id: str,
) -> None:
    """FM Finalize + Ralph Loop Pass 2 — 최종 Excel 생성."""
    from celery.exceptions import SoftTimeLimitExceeded

    from app.services.financial_model_service import run_finalize_and_generate

    logger.info(
        "Celery: FM Finalize + Ralph Pass 2 시작 (fm=%s, txn=%s)",
        fm_id,
        transaction_id,
    )
    try:
        _run_async(
            run_finalize_and_generate(
                fm_id=uuid.UUID(fm_id),
                transaction_id=uuid.UUID(transaction_id),
            )
        )
    except SoftTimeLimitExceeded:
        logger.warning("FM Finalize + Ralph Pass 2 soft_time_limit 초과 (fm=%s)", fm_id)
        _rollback_fm_to_failed(fm_id, transaction_id, "작업 시간 초과 (soft_time_limit)")
    except Exception:
        logger.exception("FM Finalize + Ralph Pass 2 실패 (fm=%s)", fm_id)
        try:
            raise self.retry(countdown=60)
        except self.MaxRetriesExceededError:
            _rollback_fm_to_failed(fm_id, transaction_id, "최대 재시도 초과")
            raise
