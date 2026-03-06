"""VcCompany 매출 데이터 하이브리드 시딩 — DB 크로스레퍼런스 + API 직접 호출.

Phase 1: SICompany -> VcCompany 크로스레퍼런스 (DB 내부)
  - corp_reg_no(하이픈 제거) = jurir_no 매칭
  - 단위 변환: SICompany.revenue(원) -> VcCompany.revenue(억원)

Phase 2: 공공데이터포털 API 직접 호출 (잔여분)
  - GetFinaStatInfoService_V2/getSummFinaStat_V2
  - Rate limit: 분당 90회 (공식 한도 100의 90%)
  - 연도 전략: primary_year -> fallback primary_year - 1

사용법:
    cd deal-mgmt
    python -m scripts.seed_vc_revenue_data [--limit 9000] [--year 2024] [--phase1-only] [--phase2-only] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 상수 ──
FINA_STAT_BASE = "/1160100/service/GetFinaStatInfoService_V2/getSummFinaStat_V2"
RATE_PER_MINUTE = 90  # 공식 한도 100의 90%
UPDATE_CHUNK = 200  # DB 업데이트 단위
BATCH_SIZE = 500  # API 호출 배치 단위
WON_TO_EOK = 100_000_000  # 원 -> 억원 변환 계수


# ── API 응답 파싱 유틸 (seed_revenue_data.py 패턴) ──


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


def _extract_revenue(items: list[dict]) -> float | None:
    """요약재무제표 항목에서 매출액(enpSaleAmt) 추출.

    유효 금액 필드가 가장 많은 item을 선택하여 매출액을 반환한다.
    """
    if not items:
        return None

    # 유효 금액 필드가 가장 많은 item 선택
    best_item = max(
        items,
        key=lambda item: sum(
            1
            for field in ("enpSaleAmt", "enpBzopPft", "enpCrtmNpf", "enpTastAmt")
            if _parse_numeric(item.get(field)) is not None
        ),
    )

    return _parse_numeric(best_item.get("enpSaleAmt"))


# ── Phase 1: DB 크로스레퍼런스 ──


async def phase1_cross_reference(session: AsyncSession, year: int) -> int:
    """SICompany.revenue -> VcCompany.revenue 크로스레퍼런스.

    매칭 조건: REPLACE(REPLACE(vc.corp_reg_no, '-', ''), ' ', '') = si.jurir_no
    단위 변환: SICompany.revenue(원) / 100,000,000 = VcCompany.revenue(억원)
    """
    logger.info("[Phase 1] SICompany -> VcCompany 크로스레퍼런스 시작")

    # SQL UPDATE JOIN: corp_reg_no(정규화) = jurir_no 매칭
    # SICompany.revenue는 원 단위, VcCompany.revenue는 억원 단위
    sql = text("""
        UPDATE vc_companies vc
        SET
            revenue = ROUND(si.revenue / :divisor, 2),
            revenue_year = si.revenue_year
        FROM si_companies si
        WHERE
            REPLACE(REPLACE(vc.corp_reg_no, '-', ''), ' ', '') = si.jurir_no
            AND si.revenue IS NOT NULL
            AND vc.revenue IS NULL
    """)

    result = await session.execute(sql, {"divisor": WON_TO_EOK})
    updated = result.rowcount  # type: ignore[union-attr]
    await session.commit()

    logger.info("[Phase 1] 크로스레퍼런스 완료: %d건 업데이트", updated)
    return updated


# ── Phase 2: API 직접 호출 ──


async def _fetch_revenue(
    client: httpx.AsyncClient,
    api_key: str,
    crno: str,
    biz_year: str,
) -> tuple[float | None, str | None]:
    """단일 기업 매출액 조회. (매출액(원), 사업연도) 반환."""
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
        revenue = _extract_revenue(items)
        if revenue is not None:
            return revenue, biz_year
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.debug("API 호출 실패 (crno=%s): %s", crno, exc)
    except Exception as exc:
        logger.debug("예외 (crno=%s): %s", crno, exc)
    return None, None


async def _wait_rate_limit(minute_start: float, minute_calls: int) -> tuple[float, int]:
    """Rate limit 대기. 분당 RATE_PER_MINUTE 호출 초과 시 대기."""
    if minute_calls >= RATE_PER_MINUTE:
        elapsed = time.monotonic() - minute_start
        if elapsed < 60:
            wait = 60 - elapsed + 1
            logger.info("  Rate limit 대기: %.0f초", wait)
            await asyncio.sleep(wait)
        return time.monotonic(), 0
    return minute_start, minute_calls


async def _process_api_batch(
    session: AsyncSession,
    client: httpx.AsyncClient,
    api_key: str,
    companies: list[tuple[int, str]],  # (id, corp_reg_no)
    primary_year: str,
    fallback_year: str,
    *,
    minute_start: float,
    minute_calls: int,
) -> tuple[int, int, float, int]:
    """배치 내 기업들의 매출 데이터를 API로 수집하고 DB에 저장한다.

    반환: (성공 건수, API 호출 건수, minute_start, minute_calls)
    """
    from app.models.vc_company import VcCompany

    updates: list[tuple[int, float, int]] = []  # (id, revenue_eok, year)
    api_calls = 0
    success_count = 0

    for vc_id, corp_reg_no in companies:
        # Rate limit 체크
        minute_start, minute_calls = await _wait_rate_limit(minute_start, minute_calls)

        # corp_reg_no 정규화: 하이픈/공백 제거 -> 13자리 법인등록번호
        crno = corp_reg_no.replace("-", "").replace(" ", "")

        # 1차: primary_year 시도
        revenue_won, year = await _fetch_revenue(client, api_key, crno, primary_year)
        api_calls += 1
        minute_calls += 1

        # 2차: fallback_year
        if revenue_won is None and fallback_year != primary_year:
            minute_start, minute_calls = await _wait_rate_limit(minute_start, minute_calls)

            revenue_won, year = await _fetch_revenue(client, api_key, crno, fallback_year)
            api_calls += 1
            minute_calls += 1

        if revenue_won is not None and year is not None:
            # 원 -> 억원 변환
            revenue_eok = round(revenue_won / WON_TO_EOK, 2)
            updates.append((vc_id, revenue_eok, int(year)))
            success_count += 1

        # 주기적 DB 저장
        if len(updates) >= UPDATE_CHUNK:
            try:
                for uid, rev, yr in updates:
                    await session.execute(
                        update(VcCompany).where(VcCompany.id == uid).values(revenue=rev, revenue_year=yr)
                    )
                await session.commit()
                logger.info("  DB 업데이트: %d건 저장", len(updates))
            except Exception as exc:
                logger.warning("  DB 커밋 실패 (%d건 롤백): %s", len(updates), exc)
                await session.rollback()
            updates.clear()

    # 잔여 업데이트
    if updates:
        try:
            for uid, rev, yr in updates:
                await session.execute(update(VcCompany).where(VcCompany.id == uid).values(revenue=rev, revenue_year=yr))
            await session.commit()
            logger.info("  DB 업데이트: %d건 저장 (잔여)", len(updates))
        except Exception as exc:
            logger.warning("  DB 커밋 실패 (%d건 롤백): %s", len(updates), exc)
            await session.rollback()

    return success_count, api_calls, minute_start, minute_calls


async def phase2_api_fetch(
    session: AsyncSession,
    limit: int,
    year: int,
) -> tuple[int, int]:
    """Phase 2: 잔여 기업 대상 API 직접 호출.

    반환: (성공 건수, API 호출 건수)
    """
    from app.core.config import settings
    from app.models.vc_company import VcCompany

    logger.info("[Phase 2] API 직접 호출 시작 (limit=%d, year=%d)", limit, year)

    api_key = settings.DATA_GO_KR_API_KEY
    if not api_key:
        logger.error("DATA_GO_KR_API_KEY가 설정되지 않았습니다. .env에 추가하세요.")
        return 0, 0

    primary_year = str(year)
    fallback_year = str(year - 1)

    # 수집 대상: corp_reg_no IS NOT NULL AND revenue IS NULL
    query = (
        select(VcCompany.id, VcCompany.corp_reg_no)
        .where(
            VcCompany.corp_reg_no.isnot(None),
            VcCompany.revenue.is_(None),
        )
        .order_by(VcCompany.company_name)
        .limit(limit)
    )

    result = await session.execute(query)
    companies = [(row.id, row.corp_reg_no) for row in result.all()]

    if not companies:
        logger.info("[Phase 2] API 호출 대상 기업이 없습니다.")
        return 0, 0

    logger.info("[Phase 2] API 호출 대상: %d건", len(companies))

    total_success = 0
    total_api_calls = 0
    minute_start = time.monotonic()
    minute_calls = 0

    async with httpx.AsyncClient(
        base_url=settings.DATA_GO_KR_BASE_URL,
        timeout=30.0,
    ) as client:
        for i in range(0, len(companies), BATCH_SIZE):
            batch = companies[i : i + BATCH_SIZE]
            logger.info(
                "[Phase 2] 배치 %d~%d (%d건)",
                i,
                min(i + BATCH_SIZE, len(companies)),
                len(batch),
            )

            success, api_calls, minute_start, minute_calls = await _process_api_batch(
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

    logger.info(
        "[Phase 2] API 호출 완료: 성공 %d건 / 호출 %d건",
        total_success,
        total_api_calls,
    )
    return total_success, total_api_calls


# ── 메인 ──


async def main(
    limit: int = 9000,
    year: int = 2024,
    phase1_only: bool = False,
    phase2_only: bool = False,
    force: bool = False,
) -> None:
    """VcCompany 매출 데이터 하이브리드 시딩 메인."""
    from app.core.config import settings
    from app.models.vc_company import VcCompany

    print("=" * 60)
    print("  VcCompany 매출 데이터 하이브리드 시딩")
    print("  Phase 1: SICompany 크로스레퍼런스")
    print("  Phase 2: 공공데이터포털 API 직접 호출")
    print("=" * 60)

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    phase1_count = 0
    phase2_success = 0
    phase2_api_calls = 0

    async with session_factory() as session:
        # --force: 기존 매출 데이터 초기화
        if force:
            reset_result = await session.execute(
                update(VcCompany).where(VcCompany.revenue.isnot(None)).values(revenue=None, revenue_year=None)
            )
            reset_count = reset_result.rowcount  # type: ignore[union-attr]
            await session.commit()
            logger.info("--force: VcCompany revenue %d건 초기화", reset_count)

        # 사전 통계
        total_vc = (await session.execute(select(func.count()).select_from(VcCompany))).scalar()
        has_revenue = (
            await session.execute(select(func.count()).select_from(VcCompany).where(VcCompany.revenue.isnot(None)))
        ).scalar()
        has_corp_reg = (
            await session.execute(select(func.count()).select_from(VcCompany).where(VcCompany.corp_reg_no.isnot(None)))
        ).scalar()

        logger.info(
            "사전 통계: 전체 %s건, 매출 보유 %s건, 법인등록번호 보유 %s건",
            f"{total_vc:,}" if total_vc else "0",
            f"{has_revenue:,}" if has_revenue else "0",
            f"{has_corp_reg:,}" if has_corp_reg else "0",
        )

        # Phase 1
        if not phase2_only:
            phase1_count = await phase1_cross_reference(session, year)

        # Phase 2
        if not phase1_only:
            phase2_success, phase2_api_calls = await phase2_api_fetch(session, limit, year)

        # 최종 통계
        final_revenue = (
            await session.execute(select(func.count()).select_from(VcCompany).where(VcCompany.revenue.isnot(None)))
        ).scalar()

    await engine.dispose()

    # 리포트
    print("\n" + "=" * 60)
    print("  VcCompany 매출 시딩 완료 리포트")
    print("=" * 60)
    print(f"  전체 VcCompany: {total_vc:,}건" if total_vc else "  전체 VcCompany: 0건")
    if not phase2_only:
        print(f"  Phase 1 크로스레퍼런스: {phase1_count:,}건 업데이트")
    if not phase1_only:
        print(f"  Phase 2 API 성공: {phase2_success:,}건 / 호출 {phase2_api_calls:,}건")
        print(f"  조회 연도: {year} (fallback: {year - 1})")
    print(f"  최종 매출 보유: {final_revenue:,}건" if final_revenue else "  최종 매출 보유: 0건")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VcCompany 매출 데이터 하이브리드 시딩 (DB 크로스레퍼런스 + API)")
    parser.add_argument("--limit", type=int, default=9000, help="Phase 2 최대 API 호출 수 (기본: 9000)")
    parser.add_argument("--year", type=int, default=2024, help="조회 사업연도 (기본: 2024)")
    parser.add_argument("--phase1-only", action="store_true", help="Phase 1만 실행 (DB 크로스레퍼런스)")
    parser.add_argument("--phase2-only", action="store_true", help="Phase 2만 실행 (API 호출)")
    parser.add_argument("--force", action="store_true", help="기존 매출 데이터 초기화 후 재실행")
    args = parser.parse_args()

    asyncio.run(
        main(
            limit=args.limit,
            year=args.year,
            phase1_only=args.phase1_only,
            phase2_only=args.phase2_only,
            force=args.force,
        )
    )
