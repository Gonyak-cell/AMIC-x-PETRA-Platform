"""뉴스 수집 백그라운드 태스크 — Celery 래퍼.

Cloudflare /crawl API로 추가 IB 소스를 정기 수집한다.
settings.CF_CRAWL_ENABLED=True일 때만 실제 수집 수행.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
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


async def _collect_cf_news() -> dict[str, dict[str, int]]:
    """Cloudflare /crawl 수집 파이프라인 실행."""
    from app.core.config import settings
    from app.core.database import async_session_factory
    from app.services.cf_crawl_service import CloudflareCrawlService

    if not settings.CF_CRAWL_ENABLED:
        logger.info("CF_CRAWL_ENABLED=False, 수집 건너뜀")
        return {}

    service = CloudflareCrawlService()
    try:
        async with async_session_factory() as db:
            return await service.collect_all(db)
    finally:
        await service.close()


@celery_app.task(
    name="deal_mgmt.news.collect_cf_sources",
    bind=True,
    max_retries=1,
    soft_time_limit=300,  # 5분
    acks_late=True,
)
def collect_cloudflare_sources(self) -> dict[str, dict[str, int]]:
    """Cloudflare /crawl로 추가 IB 소스 정기 수집 (매시 정각).

    Redis Lock으로 동시 실행을 방지한다 (cf_crawl_service 내부).
    """
    from celery.exceptions import SoftTimeLimitExceeded

    logger.info("Celery: CF 뉴스 수집 시작")
    try:
        results = _run_async(_collect_cf_news())
        total_new = sum(r.get("new", 0) for r in results.values())
        logger.info("Celery: CF 뉴스 수집 완료 — %d개 소스, %d건 신규", len(results), total_new)
        return results
    except SoftTimeLimitExceeded:
        logger.warning("CF 뉴스 수집 soft_time_limit 초과")
        return {}
    except Exception:
        logger.exception("CF 뉴스 수집 실패")
        raise self.retry(countdown=120)
