"""금융위 기업기본정보 API → si_companies 기본정보 배치 수집 스크립트.

공공데이터포털 GetCorpOutline_V2 API를 호출하여
법인등록번호(crno = jurir_no) 기반으로 대표자, 설립일, 주소, 종업원수 등을 수집, DB에 저장한다.

한번 수집한 데이터는 PostgreSQL에 영구 저장되며, --force 옵션으로 재수집 가능.

사용법:
    cd deal-mgmt
    python -m scripts.seed_corp_basic_data [--limit 9500] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# data.go.kr API 설정
CORP_OUTLINE_BASE = "/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2"
RATE_PER_MINUTE = 90  # 공식 한도 100의 90%
UPDATE_CHUNK = 200  # DB 업데이트 단위


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


def _extract_field(item: dict, key: str) -> str:
    """항목에서 필드 추출, 빈 문자열 정규화."""
    val = (item.get(key) or "").strip()
    return val if val and val != "-" else ""


async def fetch_corp_basic(
    client: httpx.AsyncClient,
    api_key: str,
    crno: str,
) -> dict | None:
    """단일 기업 기본정보 조회. 파싱된 dict 반환."""
    try:
        resp = await client.get(
            CORP_OUTLINE_BASE,
            params={
                "serviceKey": api_key,
                "resultType": "json",
                "crno": crno,
                "numOfRows": "5",
                "pageNo": "1",
            },
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not _check_result_code(data):
            return None
        items = _parse_items(data)
        if not items:
            return None
        item = items[0]
        return {
            "representative": _extract_field(item, "enpRprFnm"),
            "founded_date": _extract_field(item, "enpEstbDt"),
            "address": _extract_field(item, "enpBsadr"),
            "homepage": _extract_field(item, "enpHmpgUrl"),
            "employee_count": _extract_field(item, "enpEmpeCnt"),
            "industry_name": _extract_field(item, "sicNm"),
            "main_business": _extract_field(item, "enpMainBizNm"),
            "market_type": _extract_field(item, "corpRegMrktDcd"),
            "market_type_name": _extract_field(item, "corpRegMrktDcdNm"),
            "corp_basic_base_date": _extract_field(item, "basDt"),
        }
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.debug("API 호출 실패 (crno=%s): %s", crno, type(exc).__name__)
    except Exception as exc:
        logger.debug("예외 (crno=%s): %s", crno, type(exc).__name__)
    return None


async def process_batch(
    session: AsyncSession,
    client: httpx.AsyncClient,
    api_key: str,
    companies: list[tuple[str, str]],  # (id_hex, jurir_no)
    *,
    minute_start: float,
    minute_calls: int,
) -> tuple[int, int, float, int]:
    """배치 내 기업들의 기본정보를 수집하고 DB에 저장한다.

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

        result = await fetch_corp_basic(client, api_key, jurir_no)
        api_calls += 1
        minute_calls += 1

        if result is not None:
            result["id_hex"] = company_id_hex
            result["corp_basic_synced_at"] = datetime.now(UTC)
            updates.append(result)
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


async def main(limit: int = 9500, force: bool = False) -> None:
    """기업기본정보 수집 파이프라인 메인."""
    from app.core.config import settings
    from app.models.si_company import SICompany

    print("=" * 60)
    print("  금융위 기업기본정보 → si_companies 기본정보 배치 수집")
    print("=" * 60)

    api_key = settings.DATA_GO_KR_API_KEY
    if not api_key:
        logger.error("DATA_GO_KR_API_KEY가 설정되지 않았습니다. .env에 추가하세요.")
        return

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
                    SICompany.corp_basic_synced_at.is_(None),
                )
                .order_by(SICompany.company_name)
                .limit(limit)
            )

        result = await session.execute(query)
        companies = [(str(row.id), row.jurir_no) for row in result.all()]

        if not companies:
            logger.info("수집 대상 기업이 없습니다 (기본정보가 이미 수집됨).")
            await engine.dispose()
            return

        logger.info(
            "[Step 1] 수집 대상: %d건 (limit=%d, force=%s)",
            len(companies),
            limit,
            force,
        )

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
        synced_count = (
            await session.execute(
                select(func.count()).select_from(SICompany).where(SICompany.corp_basic_synced_at.isnot(None))
            )
        ).scalar() or 0

    await engine.dispose()

    print("\n" + "=" * 60)
    print("  기업기본정보 수집 완료 리포트")
    print("=" * 60)
    print(f"  수집 대상: {len(companies):,}건")
    print(f"  API 호출: {total_api_calls:,}건")
    print(f"  수집 성공: {total_success:,}건")
    print(f"  DB 기본정보 보유 기업 총계: {synced_count:,}건")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="금융위 기업기본정보 → si_companies 기본정보 수집")
    parser.add_argument(
        "--limit",
        type=int,
        default=9500,
        help="1회 최대 처리 건수 (기본: 9500)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 기본정보 데이터 재조회",
    )
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, force=args.force))
