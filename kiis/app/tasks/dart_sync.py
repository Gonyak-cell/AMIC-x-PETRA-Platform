"""DART 공시 주기 동기화 태스크

전체 Company를 순회하며 DisclosureService.sync_disclosures()를 호출한다.
기업별 에러를 격리하여 한 기업 실패 시에도 나머지는 계속 처리한다.
"""

import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.company import Company
from app.services.disclosure_service import DisclosureService

logger = logging.getLogger(__name__)


async def run_dart_sync() -> dict:
    """DART 공시를 동기화한다.

    Returns:
        {"total": int, "synced": int, "errors": int}
    """
    logger.info("DART 공시 동기화 시작")
    synced = 0
    errors = 0

    async with async_session_factory() as db:
        result = await db.execute(select(Company.corp_code).where(Company.corp_code.isnot(None)))
        corp_codes = [row[0] for row in result.all()]

    total = len(corp_codes)
    svc = DisclosureService()

    for corp_code in corp_codes:
        try:
            async with async_session_factory() as db:
                await svc.sync_disclosures(db, corp_code)
                await db.commit()
                synced += 1
        except Exception:
            errors += 1
            logger.exception("DART 동기화 실패: corp_code=%s", corp_code)

    logger.info("DART 공시 동기화 완료: total=%d, synced=%d, errors=%d", total, synced, errors)
    return {"total": total, "synced": synced, "errors": errors}
