"""KIIS DB 통계 조회 (deploy.yml 시드 조건 판단용).

pef_funds, companies(GP) 테이블 통계를 JSON으로 출력한다.
API 엔드포인트는 JWT 인증이 필요하므로, 배포 시 직접 DB를 쿼리한다.

사용법:
    python -m scripts.db_stats
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    """pef_funds, companies GP 통계를 JSON으로 출력."""
    from app.core.config import settings
    from app.models.company import Company
    from app.models.gp_fund import PEFFund

    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with AsyncSession(engine) as session:
            pef_count = (await session.execute(select(func.count()).select_from(PEFFund))).scalar() or 0

            gp_count = (
                await session.execute(select(func.count()).select_from(Company).where(Company.is_gp.is_(True)))
            ).scalar() or 0

            commitment_count = (
                await session.execute(
                    select(func.count()).select_from(Company).where(Company.gp_total_commitment.isnot(None))
                )
            ).scalar() or 0
    finally:
        await engine.dispose()

    print(
        json.dumps(
            {
                "pef_funds_count": pef_count,
                "gp_count": gp_count,
                "gp_with_commitment_count": commitment_count,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
