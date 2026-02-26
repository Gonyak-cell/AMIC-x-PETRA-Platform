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
    ralph_max_cost_usd: float = 15.0,
) -> None:
    """FM Ralph Loop Pass 1 — VDR 추출 + 초안 Excel 생성."""
    from app.services.financial_model_service import _run_vdr_extraction_and_ralph

    logger.info(
        "Celery: FM Ralph Pass 1 시작 (fm=%s, txn=%s)",
        fm_id,
        transaction_id,
    )
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
    from app.services.financial_model_service import run_finalize_and_generate

    logger.info(
        "Celery: FM Finalize + Ralph Pass 2 시작 (fm=%s, txn=%s)",
        fm_id,
        transaction_id,
    )
    _run_async(
        run_finalize_and_generate(
            fm_id=uuid.UUID(fm_id),
            transaction_id=uuid.UUID(transaction_id),
        )
    )
