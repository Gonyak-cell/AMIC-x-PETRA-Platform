"""기업 데이터 수집 태스크 (T-I13).

> 마지막 수정: 2026-02-10 17:39:59

DataCollectionPipeline을 실행하여 Company 레코드를 upsert한다.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any

from src.api.tasks.celery_app import celery_app
from src.api.tasks.serializers import im_data_to_dict

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Celery 워커에서 코루틴을 안전하게 실행한다."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


@celery_app.task(bind=True, name="fetch_company", max_retries=3, acks_late=True)
def fetch_company_task(self: Any, corp_code: str) -> dict[str, Any]:
    """DART API로 기업 데이터를 수집하고 Company 레코드를 upsert한다.

    Args:
        corp_code: DART 기업 코드.

    Returns:
        수집 결과 dict (corp_code, status, data 요약).
    """
    try:
        from src.api.config import get_config
        from src.data_ingestor.pipeline import DataCollectionPipeline, PipelineConfig

        api_config = get_config()
        config = PipelineConfig(dart_api_key=api_config.dart_api_key)
        result = _run_async(_collect(config, corp_code))

        if not result.is_success:
            raise RuntimeError(f"수집 실패: {result.errors}")

        data_dict = im_data_to_dict(result.data) if result.data else {}

        return {
            "corp_code": corp_code,
            "status": "COMPLETED",
            "warnings": result.warnings,
            "data": data_dict,
        }

    except Exception as exc:
        logger.error("기업 데이터 수집 실패 (corp_code=%s): %s", corp_code, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        return {
            "corp_code": corp_code,
            "status": "FAILED",
            "error": str(exc),
        }


async def _collect(config: Any, corp_code: str) -> Any:
    """DataCollectionPipeline을 비동기로 실행한다."""
    from src.data_ingestor.pipeline import DataCollectionPipeline

    async with DataCollectionPipeline(config) as pipeline:
        return await pipeline.collect(corp_code)
