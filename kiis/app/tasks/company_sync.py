"""DART 기업 목록 DB 동기화 태스크

DART corpCode.xml ZIP 파일을 파싱하여 companies 테이블에
bulk upsert한다. 선택적으로 상장사 상세 enrichment를 수행한다.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import async_session_factory
from app.models.company import Company
from app.services.dart_service import DARTService

logger = logging.getLogger(__name__)

# Enrichment 배치 크기 (DART rate limit: 900 req/min)
_ENRICH_BATCH_SIZE = 50


async def sync_companies_from_dart(enrich_listed: bool = True) -> dict:
    """DART 기업 목록을 DB에 동기화한다.

    Step 1: corpCode.xml ZIP → 전체 기업 bulk upsert (corp_code, corp_name, stock_code)
    Step 2 (enrich_listed=True): 상장사 /company.json 호출 → corp_cls, stock_name 등 갱신

    Args:
        enrich_listed: True이면 상장사(stock_code 존재) 대상 상세정보 enrichment 수행.

    Returns:
        {"total": int, "upserted": int, "enriched": int, "errors": int}
    """
    logger.info("DART 기업 동기화 시작 (enrich_listed=%s)", enrich_listed)

    svc = DARTService()
    try:
        corp_items = await svc.get_corp_codes()
    finally:
        await svc.close()

    total = len(corp_items)
    logger.info("DART corpCode.xml 파싱 완료: %d건", total)

    if total == 0:
        return {"total": 0, "upserted": 0, "enriched": 0, "errors": 0}

    # Step 1: Bulk upsert
    rows = [
        {
            "corp_code": item.corp_code,
            "corp_name": item.corp_name,
            "stock_code": item.stock_code or None,
            "corp_cls": "E" if not item.stock_code else None,
        }
        for item in corp_items
    ]

    # 배치 단위 upsert (메모리 효율)
    batch_size = 5000
    upserted = 0
    async with async_session_factory() as db:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            stmt = pg_insert(Company).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["corp_code"],
                set_={
                    "corp_name": stmt.excluded.corp_name,
                    "stock_code": stmt.excluded.stock_code,
                },
            )
            await db.execute(stmt)
            upserted += len(batch)
        await db.commit()

    logger.info("Bulk upsert 완료: %d건", upserted)

    # Step 2: 상장사 enrichment
    enriched = 0
    errors = 0

    if enrich_listed:
        async with async_session_factory() as db:
            result = await db.execute(
                select(Company.id, Company.corp_code).where(
                    Company.stock_code.isnot(None),
                    Company.stock_code != "",
                )
            )
            listed_companies = result.all()

        logger.info("상장사 enrichment 대상: %d건", len(listed_companies))

        svc = DARTService()
        try:
            for company_id, corp_code in listed_companies:
                try:
                    info = await svc.get_company_info(corp_code)
                    async with async_session_factory() as db:
                        await db.execute(
                            select(Company).where(Company.id == company_id)
                        )
                        stmt = (
                            Company.__table__.update()
                            .where(Company.id == company_id)
                            .values(
                                corp_cls=info.corp_cls or None,
                                stock_name=info.stock_name or None,
                                corp_name_eng=info.corp_name_eng or None,
                                ceo_nm=info.ceo_nm or None,
                                jurir_no=info.jurir_no or None,
                                bizr_no=info.bizr_no or None,
                                adres=info.adres or None,
                                hm_url=info.hm_url or None,
                                ir_url=info.ir_url or None,
                                phn_no=info.phn_no or None,
                                fax_no=info.fax_no or None,
                                induty_code=info.induty_code or None,
                                est_dt=info.est_dt or None,
                                acc_mt=info.acc_mt or None,
                            )
                        )
                        await db.execute(stmt)
                        await db.commit()
                    enriched += 1
                except Exception:
                    errors += 1
                    logger.warning("상장사 enrichment 실패: corp_code=%s", corp_code)
        finally:
            await svc.close()

        logger.info(
            "상장사 enrichment 완료: enriched=%d, errors=%d",
            enriched,
            errors,
        )

    result = {
        "total": total,
        "upserted": upserted,
        "enriched": enriched,
        "errors": errors,
    }
    logger.info("DART 기업 동기화 완료: %s", result)
    return result
