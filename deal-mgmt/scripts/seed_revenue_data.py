"""금융위 기업재무정보 API → si_companies 전체 재무 필드 배치 수집 스크립트.

공공데이터포털 GetFinaStatInfoService_V2/getSummFinaStat_V2 API를 호출하여
법인등록번호(crno = jurir_no) 기반으로 매출액, 영업이익, 당기순이익, 자산총계,
부채총계, 자본총계, 자본금, 부채비율, 법인세차감전순이익을 수집, DB에 저장한다.

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
from datetime import UTC, datetime

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

# API 필드 → DB 컬럼 매핑 (금액 필드)
_FINA_AMOUNT_FIELDS: list[tuple[str, str]] = [
    ("enpSaleAmt", "revenue"),
    ("enpBzopPft", "operating_profit"),
    ("enpCrtmNpf", "net_income"),
    ("enpTastAmt", "total_assets"),
    ("enpTdbtAmt", "total_debt"),
    ("enpTcptAmt", "total_equity"),
    ("enpCptlAmt", "capital_amount"),
    ("fnclDebtRto", "debt_ratio"),
    ("iclsPalClcAmt", "pretax_income"),
]

# API 필드 → DB 컬럼 매핑 (메타 필드)
_FINA_META_FIELDS: list[tuple[str, str]] = [
    ("basDt", "fina_base_date"),
    ("fnclDcd", "fina_report_code"),
    ("fnclDcdNm", "fina_report_name"),
]


def _parse_numeric(val: str | None) -> float | None:
    """쉼표 제거 후 숫자 변환. 빈 문자열이나 '0'은 None."""
    if not val:
        return None
    cleaned = val.strip().replace(",", "")
    if not cleaned or cleaned == "0":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_fina_stat(items: list[dict]) -> dict[str, float | str | None]:
    """요약재무제표 항목에서 전체 재무 필드 추출.

    데이터 출처 일관성을 위해 유효 금액 필드가 가장 많은 단일 item을 선택한 후
    모든 필드를 일괄 추출한다 (보고서 유형 혼재 방지).
    """
    all_fields = [*_FINA_AMOUNT_FIELDS, *_FINA_META_FIELDS]
    if not items:
        return {db_col: None for _, db_col in all_fields}

    # 유효 금액 필드가 가장 많은 item 선택
    best_item = max(
        items,
        key=lambda item: sum(
            1 for api_field, _ in _FINA_AMOUNT_FIELDS if _parse_numeric(item.get(api_field)) is not None
        ),
    )

    result: dict[str, float | str | None] = {}

    # 금액 필드: 숫자 변환
    for api_field, db_col in _FINA_AMOUNT_FIELDS:
        result[db_col] = _parse_numeric(best_item.get(api_field))

    # 메타 필드: 문자열 그대로
    for api_field, db_col in _FINA_META_FIELDS:
        val = (best_item.get(api_field) or "").strip()
        result[db_col] = val if val else None

    return result


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


async def fetch_fina_stat(
    client: httpx.AsyncClient,
    api_key: str,
    crno: str,
    biz_year: str,
) -> tuple[dict[str, float | str | None] | None, str | None]:
    """단일 기업 전체 재무정보 조회. (재무dict, 사업연도) 반환."""
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
        fina = _parse_fina_stat(items)
        # 하나라도 유효한 금액이 있으면 성공
        if any(fina.get(col) is not None for _, col in _FINA_AMOUNT_FIELDS):
            return fina, biz_year
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
    *,
    minute_start: float,
    minute_calls: int,
) -> tuple[int, int, float, int]:
    """배치 내 기업들의 재무정보를 수집하고 DB에 저장한다.

    반환: (성공 건수, API 호출 건수, minute_start, minute_calls)
    """
    from app.models.si_company import SICompany

    updates: list[dict] = []
    api_calls = 0
    success_count = 0

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
        fina, year = await fetch_fina_stat(client, api_key, jurir_no, primary_year)
        api_calls += 1
        minute_calls += 1

        # 2차: fallback_year
        if fina is None and fallback_year != primary_year:
            if minute_calls >= RATE_PER_MINUTE:
                elapsed = time.monotonic() - minute_start
                if elapsed < 60:
                    await asyncio.sleep(60 - elapsed + 1)
                minute_start = time.monotonic()
                minute_calls = 0

            fina, year = await fetch_fina_stat(client, api_key, jurir_no, fallback_year)
            api_calls += 1
            minute_calls += 1

        if fina is not None and year is not None:
            updates.append(
                {
                    "id_hex": company_id_hex,
                    **fina,
                    "revenue_year": int(year),
                    "fina_stat_synced_at": datetime.now(UTC),
                }
            )
            success_count += 1

        # 주기적 DB 저장
        if len(updates) >= UPDATE_CHUNK:
            try:
                for upd in updates:
                    cid = upd["id_hex"]
                    vals = {k: v for k, v in upd.items() if k != "id_hex"}
                    await session.execute(update(SICompany).where(SICompany.id == cid).values(**vals))
                await session.commit()
                logger.info("  DB 업데이트: %d건 저장", len(updates))
            except Exception as exc:
                logger.warning("  DB 커밋 실패 (%d건 롤백): %s", len(updates), exc)
                await session.rollback()
            updates.clear()

    # 잔여 업데이트
    if updates:
        try:
            for upd in updates:
                cid = upd["id_hex"]
                vals = {k: v for k, v in upd.items() if k != "id_hex"}
                await session.execute(update(SICompany).where(SICompany.id == cid).values(**vals))
            await session.commit()
            logger.info("  DB 업데이트: %d건 저장 (잔여)", len(updates))
        except Exception as exc:
            logger.warning("  DB 커밋 실패 (%d건 롤백): %s", len(updates), exc)
            await session.rollback()

    return success_count, api_calls, minute_start, minute_calls


async def main(limit: int = 9000, year: int = 2024, force: bool = False) -> None:
    """재무정보 수집 파이프라인 메인."""
    from app.core.config import settings
    from app.models.si_company import SICompany

    print("=" * 60)
    print("  금융위 기업재무정보 → si_companies 전체 재무 필드 배치 수집")
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
                .where(
                    SICompany.jurir_no.isnot(None),
                    SICompany.fina_stat_synced_at.is_(None),
                )
                .order_by(SICompany.company_name)
                .limit(limit)
            )

        result = await session.execute(query)
        companies = [(str(row.id), row.jurir_no) for row in result.all()]

        if not companies:
            logger.info("수집 대상 기업이 없습니다 (재무정보가 이미 수집됨).")
            await engine.dispose()
            return

        logger.info("[Step 1] 수집 대상: %d건 (limit=%d, force=%s)", len(companies), limit, force)

        # API 호출
        total_success = 0
        total_api_calls = 0
        batch_size = 500
        minute_start = time.monotonic()
        minute_calls = 0

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

                success, api_calls, minute_start, minute_calls = await process_batch(
                    session,
                    client,
                    api_key,
                    batch,
                    primary_year,
                    fallback_year,
                    minute_start=minute_start,
                    minute_calls=minute_calls,
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

        fina_count = (
            await session.execute(text("SELECT COUNT(*) FROM si_companies WHERE fina_stat_synced_at IS NOT NULL"))
        ).scalar()

    await engine.dispose()

    print("\n" + "=" * 60)
    print("  재무정보 수집 완료 리포트")
    print("=" * 60)
    print(f"  수집 대상: {len(companies):,}건")
    print(f"  수집 성공: {total_success:,}건")
    print(f"  API 호출: {total_api_calls:,}건")
    print(f"  조회 연도: {primary_year} (fallback: {fallback_year})")
    print(f"  DB 매출액 보유 기업 총계: {rev_count:,}건")
    print(f"  DB 재무정보 동기화 총계: {fina_count:,}건")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="금융위 기업재무정보 → si_companies 전체 재무 필드 수집")
    parser.add_argument("--limit", type=int, default=9000, help="1회 최대 처리 건수 (기본: 9000)")
    parser.add_argument("--year", type=int, default=2024, help="조회 사업연도 (기본: 2024)")
    parser.add_argument("--force", action="store_true", help="기존 재무 데이터 재조회")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, year=args.year, force=args.force))
