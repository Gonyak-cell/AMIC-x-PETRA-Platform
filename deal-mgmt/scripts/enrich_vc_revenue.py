"""VcCompany 매출액 교차 참조 — SICompany 기존 매출 데이터 복사.

기존 SICompany 테이블의 revenue 데이터를 VcCompany에 company_name 매칭으로 복사한다.
DART API 점진적 enrichment는 별도 Celery 태스크로 구현 예정.

사용법:
    cd deal-mgmt
    python -m scripts.enrich_vc_revenue
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from decimal import Decimal

from sqlalchemy import bindparam, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


async def _get_engine_and_session() -> tuple:
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def enrich_from_si_companies(session: AsyncSession) -> int:
    """SICompany.revenue → VcCompany.revenue 교차 참조 (company_name exact match)."""
    from app.models.si_company import SICompany
    from app.models.vc_company import VcCompany

    # 1. SICompany에서 매출 보유 기업 로드
    si_result = await session.execute(
        select(SICompany.company_name, SICompany.revenue).where(
            SICompany.revenue.isnot(None),
            SICompany.revenue > 0,
        )
    )
    si_revenues: dict[str, Decimal] = {}
    for row in si_result:
        name = row[0].strip() if row[0] else None
        if name and row[1]:
            # SICompany.revenue는 원(KRW) 단위, VcCompany.revenue는 억원 단위이므로 변환
            si_revenues[name] = Decimal(str(row[1])) / Decimal("100000000")

    if not si_revenues:
        logger.info("SICompany에 매출 데이터 없음 — 교차참조 스킵")
        return 0

    logger.info("SICompany 매출 보유 기업: %d건", len(si_revenues))

    # 2. VcCompany에서 매출 미보유 기업 중 매칭
    vc_result = await session.execute(select(VcCompany.id, VcCompany.company_name).where(VcCompany.revenue.is_(None)))

    matched = 0
    batch_updates: list[dict] = []

    for vc_row in vc_result:
        vc_id = vc_row[0]
        vc_name = vc_row[1].strip() if vc_row[1] else None
        if not vc_name:
            continue

        revenue = si_revenues.get(vc_name)
        if revenue is not None:
            batch_updates.append({"_vc_id": vc_id, "_revenue_val": revenue})
            matched += 1

        # 배치 단위 벌크 UPDATE (Core 테이블 사용 — ORM bulk update 비호환 우회)
        if len(batch_updates) >= BATCH_SIZE:
            tbl = VcCompany.__table__
            stmt = tbl.update().where(tbl.c.id == bindparam("_vc_id")).values(revenue=bindparam("_revenue_val"))
            await session.execute(stmt, batch_updates)
            batch_updates.clear()
            logger.info("매출 교차참조: %d건 업데이트...", matched)

    # 잔여 배치
    if batch_updates:
        tbl = VcCompany.__table__
        stmt = tbl.update().where(tbl.c.id == bindparam("_vc_id")).values(revenue=bindparam("_revenue_val"))
        await session.execute(stmt, batch_updates)

    await session.commit()
    logger.info("매출 교차참조 완료: SICompany→VcCompany %d건 매칭", matched)
    return matched


async def main() -> None:
    engine, session_factory = await _get_engine_and_session()
    async with session_factory() as session:
        await enrich_from_si_companies(session)
    await engine.dispose()
    logger.info("VcCompany 매출 enrichment 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VcCompany 매출 교차참조")
    parser.parse_args()
    asyncio.run(main())
