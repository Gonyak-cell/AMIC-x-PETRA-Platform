"""GP 프로파일 동기화 태스크

공공데이터포털 자산운용사 정보를 Company 테이블에 주기적으로 동기화한다.
"""

import logging

from app.core.database import async_session_factory
from app.services.public_data_service import PublicDataService

logger = logging.getLogger(__name__)


async def run_gp_profile_sync() -> dict[str, int | list[str]]:
    """공공데이터 GP 프로파일을 Company에 동기화한다.

    Returns:
        {"total_api_items": int, "created": int, "updated": int,
         "aliases_added": int, "errors": list[str]}
    """
    logger.info("GP 프로파일 동기화 태스크 시작")

    svc = PublicDataService()
    try:
        async with async_session_factory() as db:
            result = await svc.sync_gp_profiles(db)
    finally:
        await svc.close()

    summary = {
        "total_api_items": result.total_api_items,
        "created": result.created,
        "updated": result.updated,
        "aliases_added": result.aliases_added,
        "errors": result.errors,
    }
    logger.info("GP 프로파일 동기화 태스크 완료: %s", summary)
    return summary
