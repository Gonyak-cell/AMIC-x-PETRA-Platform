"""금융위 기업재무정보 API → si_companies.revenue 배치 수집 스크립트.

공공데이터포털 GetFinaStatInfoService_V2/getSummFinaStat_V2 API를 호출하여
법인등록번호(crno = jurir_no) 기반으로 매출액(enpSaleAmt)을 수집, DB에 저장한다.

한번 수집한 데이터는 PostgreSQL에 영구 저장되며, 매년 --force 옵션으로 갱신 가능.

사용법:
    cd deal-mgmt
    python -m scripts.seed_revenue_data [--limit 9000] [--year 2024] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# data.go.kr API 설정
FINA_STAT_BASE = "/1160100/service/GetFinaStatInfoService_V2/getSummFinaStat_V2"
RATE_PER_MINUTE = 90  # 공식 한도 100의 90%
UPDATE_CHUNK = 200  # DB 업데이트 단위


def _parse_sale_amt(items: list[dict]) -> str | None:
    """요약재무제표 항목에서 매출금액(enpSaleAmt) 추출."""
    for item in items:
        val = (item.get("enpSaleAmt") or "").strip()
        if val and val != "0":
            return val
    return None


def _parse_items(data: dict) -> list[dict]:
    """data.go.kr 공통 응답 파싱: response.body.items.item[] 추출."""
    try:
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})
        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
        else:
            return []
        if isinstance(item_list, dict):
            return [item_list]
        return item_list if isinstance(item_list, list) else []
    except (AttributeError, TypeError):
        return []


def _check_result_code(data: dict) -> bool:
    """응답 코드 검증. 정상이면 True."""
    header = data.get("response", {}).get("header", {})
    code = header.get("resultCode", "99")
    return code == "00"


async def fetch_revenue(
    client: httpx.AsyncClient,
    api_key: str,
    crno: str,
    biz_year: str,
) -> tuple[float | None, str | None]:
    """단일 기업 매출액 조회. (매출액, 사업연도) 반환."""
    try:
        resp = await client.get(
            FINA_STAT_BASE,
            params={
                "serviceKey": api_key,
                "resultType": "json",
                "crno": crno,
                "bizYear": biz_year,
                "numOfRows": "10",
                "pageNo": "1",
            },
        )
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        if not _check_result_code(data):
            return None, None
        items = _parse_items(data)
        sale_amt = _parse_sale_amt(items)
        if sale_amt:
            # 숫자 파싱 (쉼표 제거)
            cleaned = sale_amt.replace(",", "")
            try:
                return float(cleaned), biz_year
            except ValueError:
                return None, None
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.debug("API 호출 실패 (crno=%s): %s", crno, exc)
    except Exception as exc:
        logger.debug("예외 (crno=%s): %s", crno, exc)
    return None, None


async def process_batch(
    session: AsyncSession,
    client: httpx.AsyncClient,
    api_key: str,
    companies: list[tuple[str, str]],  # (id_hex, jurir_no)
    primary_year: str,
    fallback_year: str,
) -> tuple[int, int]:
    """배치 내 기업들의 매출액을 수집하고 DB에 저장한다.

    반환: (성공 건수, API 호출 건수)
    """
    from app.models.si_company import SICompany

    updates: list[dict] = []
    api_calls = 0
    minute_start = time.monotonic()
    minute_calls = 0

    for company_id_hex, jurir_no in companies:
        # Rate limit: 분당 90회
        if minute_calls >= RATE_PER_MINUTE:
            elapsed = time.monotonic() - minute_start
            if elapsed < 60:
                wait = 60 - elapsed + 1
                logger.info("  Rate limit 대기: %.0f초", wait)
                await asyncio.sleep(wait)
            minute_start = time.monotonic()
            minute_calls = 0

        # 1차: primary_year 시도
        revenue, year = await fetch_revenue(client, api_key, jurir_no, primary_year)
        api_calls += 1
        minute_calls += 1

        # 2차: fallback_year
        if revenue is None and fallback_year != primary_year:
            if minute_calls >= RATE_PER_MINUTE:
                elapsed = time.monotonic() - minute_start
                if elapsed < 60:
                    await asyncio.sleep(60 - elapsed + 1)
                minute_start = time.monotonic()
                minute_calls = 0

            revenue, year = await fetch_revenue(client, api_key, jurir_no, fallback_year)
            api_calls += 1
            minute_calls += 1

        if revenue is not None and year is not None:
            updates.append(
                {
                    "id_hex": company_id_hex,
                    "revenue": revenue,
                    "revenue_year": int(year),
                }
            )

        # 주기적 DB 저장
        if len(updates) >= UPDATE_CHUNK:
            for upd in updates:
                await session.execute(
                    update(SICompany)
                    .where(SICompany.id == upd["id_hex"])
                    .values(revenue=upd["revenue"], revenue_year=upd["revenue_year"])
                )
            await session.commit()
            logger.info("  DB 업데이트: %d건 저장", len(updates))
            updates.clear()

    # 잔여 업데이트
    if updates:
        for upd in updates:
            await session.execute(
                update(SICompany)
                .where(SICompany.id == upd["id_hex"])
                .values(revenue=upd["revenue"], revenue_year=upd["revenue_year"])
            )
        await session.commit()
        logger.info("  DB 업데이트: %d건 저장 (잔여)", len(updates))

    return len([u for u in updates]) if updates else 0, api_calls


async def main(limit: int = 9000, year: int = 2024, force: bool = False) -> None:
    """매출액 수집 파이프라인 메인."""
    from app.core.config import settings
    from app.models.si_company import SICompany

    print("=" * 60)
    print("  금융위 기업재무정보 → si_companies.revenue 배치 수집")
    print("=" * 60)

    api_key = settings.DATA_GO_KR_API_KEY
    if not api_key:
        logger.error("DATA_GO_KR_API_KEY가 설정되지 않았습니다. .env에 추가하세요.")
        return

    primary_year = str(year)
    fallback_year = str(year - 1)

    # DB 연결
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 수집 대상 조회
        if force:
            query = (
                select(SICompany.id, SICompany.jurir_no)
                .where(SICompany.jurir_no.isnot(None))
                .order_by(SICompany.company_name)
                .limit(limit)
            )
        else:
            query = (
                select(SICompany.id, SICompany.jurir_no)
                .where(SICompany.jurir_no.isnot(None), SICompany.revenue.is_(None))
                .order_by(SICompany.company_name)
                .limit(limit)
            )

        result = await session.execute(query)
        companies = [(str(row.id), row.jurir_no) for row in result.all()]

        if not companies:
            logger.info("수집 대상 기업이 없습니다 (revenue가 이미 채워짐).")
            await engine.dispose()
            return

        logger.info("[Step 1] 수집 대상: %d건 (limit=%d, force=%s)", len(companies), limit, force)

        # API 호출
        total_success = 0
        total_api_calls = 0
        batch_size = 500

        async with httpx.AsyncClient(
            base_url=settings.DATA_GO_KR_BASE_URL,
            timeout=30.0,
        ) as client:
            for i in range(0, len(companies), batch_size):
                batch = companies[i : i + batch_size]
                logger.info(
                    "[Step 2] 배치 %d~%d (%d건)",
                    i,
                    min(i + batch_size, len(companies)),
                    len(batch),
                )

                success, api_calls = await process_batch(
                    session,
                    client,
                    api_key,
                    batch,
                    primary_year,
                    fallback_year,
                )
                total_success += success
                total_api_calls += api_calls

                logger.info(
                    "  배치 완료: 성공 %d건, API 호출 %d건 (누적 %d/%d)",
                    success,
                    api_calls,
                    total_api_calls,
                    len(companies),
                )

        # 최종 통계
        rev_count = (
            await session.execute(text("SELECT COUNT(*) FROM si_companies WHERE revenue IS NOT NULL"))
        ).scalar()

    await engine.dispose()

    print("\n" + "=" * 60)
    print("  매출액 수집 완료 리포트")
    print("=" * 60)
    print(f"  수집 대상: {len(companies):,}건")
    print(f"  API 호출: {total_api_calls:,}건")
    print(f"  조회 연도: {primary_year} (fallback: {fallback_year})")
    print(f"  DB 매출액 보유 기업 총계: {rev_count:,}건")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="금융위 기업재무정보 → si_companies.revenue 수집")
    parser.add_argument("--limit", type=int, default=9000, help="1회 최대 처리 건수 (기본: 9000)")
    parser.add_argument("--year", type=int, default=2024, help="조회 사업연도 (기본: 2024)")
    parser.add_argument("--force", action="store_true", help="기존 매출액 데이터 재조회")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, year=args.year, force=args.force))
