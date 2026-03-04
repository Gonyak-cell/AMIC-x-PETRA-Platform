"""SI + PEF/GP 데이터 통계 조회 (deploy.yml 시드 조건 판단용).

API 엔드포인트는 JWT 인증이 필요하므로,
deploy.yml의 시드 조건 판단 시 직접 DB를 쿼리하여 통계를 출력한다.

사용법:
    python -m scripts.db_stats
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def main() -> None:
    """si_companies + pef_fund_registry + gp_profiles 통계를 JSON으로 출력."""
    from app.core.config import settings
    from app.models.gp_profile import GpProfile
    from app.models.pef_fund_registry import PefFundRegistry
    from app.models.si_company import SICompany

    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with AsyncSession(engine) as session:
            total = (await session.execute(select(func.count()).select_from(SICompany))).scalar() or 0

            revenue = (
                await session.execute(select(func.count()).select_from(SICompany).where(SICompany.revenue.isnot(None)))
            ).scalar() or 0

            corp_basic = (
                await session.execute(
                    select(func.count()).select_from(SICompany).where(SICompany.corp_basic_synced_at.isnot(None))
                )
            ).scalar() or 0

            fina_stat = (
                await session.execute(
                    select(func.count()).select_from(SICompany).where(SICompany.fina_stat_synced_at.isnot(None))
                )
            ).scalar() or 0

            pef_count = (await session.execute(select(func.count()).select_from(PefFundRegistry))).scalar() or 0

            gp_count = (await session.execute(select(func.count()).select_from(GpProfile))).scalar() or 0
    finally:
        await engine.dispose()

    print(
        json.dumps(
            {
                "si_companies_count": total,
                "revenue_count": revenue,
                "fina_stat_count": fina_stat,
                "corp_basic_count": corp_basic,
                "pef_fund_registry_count": pef_count,
                "gp_profiles_count": gp_count,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
