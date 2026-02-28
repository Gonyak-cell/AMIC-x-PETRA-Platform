"""주요 사모펀드 GP 시드 데이터를 Company 테이블에 적재하는 스크립트.

사용법:
    cd kiis
    python -m scripts.seed_gp_data
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import func, select

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory, engine
from app.models.company import Company, CompanyAlias
from app.utils.entity_resolver import normalize_company_name

logger = logging.getLogger(__name__)

# 주요 PEF GP 시드 데이터 (설계안 B 반영)
SEED_GPS: list[dict[str, str | list[str] | None]] = [
    {
        "corp_name": "MBK파트너스",
        "corp_name_eng": "MBK Partners",
        "hm_url": "https://www.mbkpartners.com",
        "aliases": ["MBK", "엠비케이"],
    },
    {
        "corp_name": "IMM인베스트먼트",
        "corp_name_eng": "IMM Investment",
        "hm_url": "https://www.imm.co.kr",
        "aliases": ["IMM", "아이엠엠"],
    },
    {
        "corp_name": "한앤컴퍼니",
        "corp_name_eng": "Hahn & Company",
        "hm_url": "https://www.hahnco.com",
        "aliases": ["한앤코", "Hahn"],
    },
    {
        "corp_name": "에이티유파트너스",
        "corp_name_eng": "ATU Partners",
        "hm_url": None,
        "aliases": ["ATU", "에이티유"],
    },
    {
        "corp_name": "스틱인베스트먼트",
        "corp_name_eng": "STIC Investments",
        "hm_url": "https://www.stic.co.kr",
        "aliases": ["STIC", "스틱"],
    },
    {
        "corp_name": "VIG파트너스",
        "corp_name_eng": "VIG Partners",
        "hm_url": "https://www.vigpartners.com",
        "aliases": ["VIG", "브이아이지"],
    },
    {
        "corp_name": "JKL파트너스",
        "corp_name_eng": "JKL Partners",
        "hm_url": None,
        "aliases": ["JKL"],
    },
    {
        "corp_name": "스카이레이크인베스트먼트",
        "corp_name_eng": "SkyLake Investment",
        "hm_url": "https://www.skylake.co.kr",
        "aliases": ["스카이레이크", "SkyLake"],
    },
    {
        "corp_name": "KCGI자산운용",
        "corp_name_eng": "KCGI",
        "hm_url": None,
        "aliases": ["KCGI", "케이씨지아이"],
    },
    {
        "corp_name": "큐캐피탈파트너스",
        "corp_name_eng": "Q Capital Partners",
        "hm_url": None,
        "aliases": ["큐캐피탈", "Q Capital"],
    },
]


async def seed_gp_data() -> tuple[int, int, int]:
    """시드 GP 데이터를 Company + CompanyAlias에 적재한다.

    Returns:
        (신규 생성, 이미 존재, 별칭 등록) 건수 튜플
    """
    created = 0
    skipped = 0
    aliases_added = 0

    async with async_session_factory() as session:
        for gp in SEED_GPS:
            corp_name = str(gp["corp_name"])
            normalized = normalize_company_name(corp_name)

            # 기존 Company 검색 (정규화 이름 매칭)
            stmt = select(Company).where(func.lower(Company.corp_name) == func.lower(corp_name))
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # 이미 존재 → is_gp 플래그만 업데이트
                if not existing.is_gp:
                    existing.is_gp = True
                    logger.info("기존 Company GP 마킹: %s (id=%d)", corp_name, existing.id)
                else:
                    logger.info("이미 존재: %s (id=%d)", corp_name, existing.id)
                company = existing
                skipped += 1
            else:
                # 신규 생성 (corp_code=None — DART 미등록)
                company = Company(
                    corp_code=None,
                    corp_name=corp_name,
                    corp_name_eng=gp.get("corp_name_eng"),
                    hm_url=gp.get("hm_url"),
                    is_gp=True,
                )
                session.add(company)
                await session.flush()  # ID 확보
                logger.info("신규 GP 생성: %s (id=%d)", corp_name, company.id)
                created += 1

            # 별칭 등록 (중복 무시)
            alias_names: list[str] = list(gp.get("aliases") or [])
            # 정규화 이름도 별칭으로 추가
            if normalized != corp_name:
                alias_names.append(normalized)

            for alias_name in alias_names:
                alias_stmt = select(CompanyAlias).where(
                    func.lower(CompanyAlias.alias_name) == func.lower(alias_name),
                    CompanyAlias.company_id == company.id,
                )
                alias_result = await session.execute(alias_stmt)
                if alias_result.scalar_one_or_none() is None:
                    alias = CompanyAlias(
                        alias_name=alias_name,
                        company_id=company.id,
                        is_manual=True,
                    )
                    session.add(alias)
                    aliases_added += 1
                    logger.info("  별칭 등록: '%s' → %s", alias_name, corp_name)

        await session.commit()

    return created, skipped, aliases_added


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logger.info("GP 시드 데이터 적재 시작...")
    created, skipped, aliases_added = await seed_gp_data()
    logger.info(
        "완료: 신규 %d건, 기존 %d건, 별칭 %d건 등록",
        created,
        skipped,
        aliases_added,
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
