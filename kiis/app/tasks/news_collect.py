"""뉴스 자동 수집 태스크

NewsService를 사용하여 RSS 피드에서 뉴스를 수집한다.
"""

import logging

from app.core.database import async_session_factory
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)


async def run_news_collect() -> dict:
    """전체 뉴스 소스에서 뉴스를 수집한다.

    Returns:
        {"sources": int, "total_collected": int}
    """
    logger.info("뉴스 자동 수집 시작")

    svc = NewsService()
    sources = 0
    total_collected = 0

    try:
        async with async_session_factory() as db:
            results = await svc.collect_all(db)
            await db.commit()

            sources = len(results)
            for r in results:
                total_collected += r.collected
    except Exception:
        logger.exception("뉴스 수집 중 예외 발생")

    logger.info("뉴스 자동 수집 완료: sources=%d, total_collected=%d", sources, total_collected)
    return {"sources": sources, "total_collected": total_collected}
