"""IB 매체 자동 수집 태스크

APScheduler에 등록되어 주기적으로 IB 매체에서 기사를 수집하고
NLP 분류 + GP 매칭을 수행한다.
"""

import logging

from app.core.database import async_session_factory
from app.core.redis import get_redis
from app.models.ib_article import IB_CRAWL_LOCK_KEY, IB_CRAWL_LOCK_TTL
from app.routers.ib_insights import _get_insight_service
from app.services.ib_crawl_service import IBCrawlService

logger = logging.getLogger(__name__)


async def run_ib_collect() -> dict:
    """IB 매체에서 기사를 수집하고 NLP 분류 + GP 매칭을 수행한다.

    Returns:
        {"collected": {...}, "classified": int}
    """
    # 동시 수집 방지 Redis Lock
    redis = get_redis()
    if redis:
        try:
            acquired = await redis.set(IB_CRAWL_LOCK_KEY, "1", nx=True, ex=IB_CRAWL_LOCK_TTL)
            if not acquired:
                logger.info("IB 수집이 이미 진행 중 (Lock 존재), 스킵")
                return {"collected": {}, "classified": 0}
        except Exception:
            logger.debug("IB 수집 Lock 획득 실패 (Redis 미가용), Lock 없이 진행", exc_info=True)

    logger.info("IB 매체 자동 수집 시작")
    crawl_svc = IBCrawlService()
    insight_svc = _get_insight_service()

    try:
        async with async_session_factory() as db:
            # 1. 4개 매체 수집
            results = await crawl_svc.collect_all(db)

            # 2. 미분류 기사 NLP 처리 + GP 매칭 (classify_unprocessed 내부에서 commit)
            classified = await insight_svc.classify_unprocessed(db)

        total_new = sum(r.get("new", 0) for r in results.values())
        logger.info("IB 자동 수집 완료: 신규 %d건, 분류 %d건", total_new, classified)
        return {"collected": results, "classified": classified}
    except Exception:
        logger.exception("IB 자동 수집 중 예외 발생")
        return {"collected": {}, "classified": 0}
    finally:
        try:
            await crawl_svc.close()
        except Exception:
            logger.debug("IB crawl 서비스 종료 실패", exc_info=True)
        if redis:
            try:
                await redis.delete(IB_CRAWL_LOCK_KEY)
            except Exception:
                logger.debug("IB 수집 Lock 해제 실패", exc_info=True)
