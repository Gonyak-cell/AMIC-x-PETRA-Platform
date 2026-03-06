# VcCompany 매출 데이터 하이브리드 시딩 — 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** VcCompany 114,964건 중 법인등록번호가 있는 기업의 매출(revenue) 데이터를 공공데이터로 채운다.

**Architecture:** Phase 1에서 SICompany에 이미 수집된 매출을 DB 내부 크로스레퍼런스로 복사하고, Phase 2에서 매칭 안 된 잔여 기업을 공공데이터포털 API로 직접 수집한다. 단위 변환(원→억원) 필수.

**Tech Stack:** Python 3.10, SQLAlchemy (async), httpx, asyncio, argparse

---

## 주의사항

- **단위 변환**: SICompany.revenue = 원(KRW), VcCompany.revenue = 억원 → `si_revenue / 100_000_000`
- **법인등록번호 정규화**: SICompany.jurir_no = 하이픈 제거 13자리, VcCompany.corp_reg_no = 하이픈 포함 가능 → `REPLACE(corp_reg_no, '-', '')` 로 매칭
- **기존 패턴 참조**: `deal-mgmt/scripts/seed_revenue_data.py` (API 호출, Rate limit, 배치 처리)

---

### Task 1: 스크립트 기본 구조 + Phase 1 (크로스레퍼런스)

**Files:**
- Create: `deal-mgmt/scripts/seed_vc_revenue_data.py`

**Step 1: 스크립트 기본 구조 작성**

`seed_revenue_data.py` 패턴을 참조하여 기본 구조를 작성한다.

```python
"""VcCompany 매출 데이터 하이브리드 시딩 스크립트.

Phase 1: SICompany → VcCompany 크로스레퍼런스 (DB 내부, API 호출 0회)
Phase 2: 잔여 기업 → 공공데이터포털 API 직접 호출

사용법:
    cd deal-mgmt
    python -m scripts.seed_vc_revenue_data [--limit 9000] [--year 2024] [--phase1-only] [--phase2-only] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 공공데이터 API 설정 ──
FINA_STAT_BASE = "/1160100/service/GetFinaStatInfoService_V2/getSummFinaStat_V2"
RATE_PER_MINUTE = 90
UPDATE_CHUNK = 200
WON_TO_EOK = 100_000_000  # 원 → 억원 변환 상수
```

**Step 2: Phase 1 함수 — SICompany → VcCompany 크로스레퍼런스**

```python
async def phase1_cross_reference(session: AsyncSession) -> int:
    """SICompany에 수집된 매출 데이터를 VcCompany로 복사.

    매칭: REPLACE(vc.corp_reg_no, '-', '') = si.jurir_no
    변환: SICompany.revenue(원) → VcCompany.revenue(억원)
    """
    sql = text("""
        UPDATE vc_companies vc
        SET
            revenue = ROUND(si.revenue / :won_to_eok, 2),
            revenue_year = si.revenue_year,
            updated_at = NOW()
        FROM si_companies si
        WHERE REPLACE(REPLACE(vc.corp_reg_no, '-', ''), ' ', '') = si.jurir_no
          AND si.revenue IS NOT NULL
          AND vc.corp_reg_no IS NOT NULL
          AND vc.revenue IS NULL
    """)
    result = await session.execute(sql, {"won_to_eok": WON_TO_EOK})
    await session.commit()
    matched = result.rowcount
    logger.info("[Phase 1] 크로스레퍼런스 완료: %d건 매출 복사", matched)
    return matched
```

**Step 3: Phase 2 헬퍼 함수 — API 응답 파싱 (seed_revenue_data.py 패턴 차용)**

```python
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


def _extract_revenue(items: list[dict]) -> float | None:
    """요약재무제표 항목에서 매출액(enpSaleAmt) 추출.

    유효 금액 필드가 가장 많은 item에서 매출액을 가져온다.
    """
    if not items:
        return None
    amount_fields = ["enpSaleAmt", "enpBzopPft", "enpCrtmNpf", "enpTastAmt"]
    best_item = max(
        items,
        key=lambda item: sum(
            1 for f in amount_fields if _parse_numeric(item.get(f)) is not None
        ),
    )
    return _parse_numeric(best_item.get("enpSaleAmt"))
```

**Step 4: Phase 2 API 호출 함수**

```python
async def fetch_revenue(
    client: httpx.AsyncClient,
    api_key: str,
    crno: str,
    biz_year: str,
) -> float | None:
    """단일 기업 매출액 조회. 억원 단위로 변환하여 반환."""
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
            return None
        data = resp.json()
        if not _check_result_code(data):
            return None
        items = _parse_items(data)
        revenue_won = _extract_revenue(items)
        if revenue_won is not None:
            return round(revenue_won / WON_TO_EOK, 2)
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.debug("API 호출 실패 (crno=%s): %s", crno, exc)
    except Exception as exc:
        logger.debug("예외 (crno=%s): %s", crno, exc)
    return None
```

**Step 5: Phase 2 배치 처리 함수**

```python
async def phase2_api_batch(
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
    """배치 내 기업 매출 수집 → DB 저장. 반환: (성공, API호출, minute_start, minute_calls)."""
    from app.models.vc_company import VcCompany

    updates: list[dict] = []
    api_calls = 0
    success_count = 0

    for company_id, corp_reg_no in companies:
        # 법인등록번호 정규화 (하이픈/공백 제거)
        crno = corp_reg_no.replace("-", "").replace(" ", "")

        # Rate limit
        if minute_calls >= RATE_PER_MINUTE:
            elapsed = time.monotonic() - minute_start
            if elapsed < 60:
                wait = 60 - elapsed + 1
                logger.info("  Rate limit 대기: %.0f초", wait)
                await asyncio.sleep(wait)
            minute_start = time.monotonic()
            minute_calls = 0

        # 1차: primary_year
        revenue = await fetch_revenue(client, api_key, crno, primary_year)
        api_calls += 1
        minute_calls += 1
        year = primary_year

        # 2차: fallback
        if revenue is None and fallback_year != primary_year:
            if minute_calls >= RATE_PER_MINUTE:
                elapsed = time.monotonic() - minute_start
                if elapsed < 60:
                    await asyncio.sleep(60 - elapsed + 1)
                minute_start = time.monotonic()
                minute_calls = 0

            revenue = await fetch_revenue(client, api_key, crno, fallback_year)
            api_calls += 1
            minute_calls += 1
            year = fallback_year

        if revenue is not None:
            updates.append({"id": company_id, "revenue": revenue, "revenue_year": int(year)})
            success_count += 1

        # 주기적 DB 저장
        if len(updates) >= UPDATE_CHUNK:
            try:
                for upd in updates:
                    await session.execute(
                        update(VcCompany)
                        .where(VcCompany.id == upd["id"])
                        .values(revenue=upd["revenue"], revenue_year=upd["revenue_year"])
                    )
                await session.commit()
                logger.info("  DB 업데이트: %d건 저장", len(updates))
            except Exception as exc:
                logger.warning("  DB 커밋 실패 (%d건 롤백): %s", len(updates), exc)
                await session.rollback()
            updates.clear()

    # 잔여 배치
    if updates:
        try:
            for upd in updates:
                await session.execute(
                    update(VcCompany)
                    .where(VcCompany.id == upd["id"])
                    .values(revenue=upd["revenue"], revenue_year=upd["revenue_year"])
                )
            await session.commit()
            logger.info("  DB 업데이트: %d건 저장 (잔여)", len(updates))
        except Exception as exc:
            logger.warning("  DB 커밋 실패 (%d건 롤백): %s", len(updates), exc)
            await session.rollback()

    return success_count, api_calls, minute_start, minute_calls
```

**Step 6: 메인 함수 + CLI**

```python
async def main(
    limit: int = 9000,
    year: int = 2024,
    force: bool = False,
    phase1_only: bool = False,
    phase2_only: bool = False,
) -> None:
    """VcCompany 매출 데이터 하이브리드 시딩 메인."""
    from app.core.config import settings
    from app.models.vc_company import VcCompany

    print("=" * 60)
    print("  VcCompany 매출 데이터 하이브리드 시딩")
    print("=" * 60)

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 사전 통계
        total_vc = (await session.execute(select(func.count()).select_from(VcCompany))).scalar() or 0
        has_crno = (
            await session.execute(
                select(func.count()).select_from(VcCompany).where(VcCompany.corp_reg_no.isnot(None))
            )
        ).scalar() or 0
        has_revenue = (
            await session.execute(
                select(func.count()).select_from(VcCompany).where(VcCompany.revenue.isnot(None))
            )
        ).scalar() or 0

        logger.info("VcCompany 현황: 전체 %d, 법인등록번호 %d, 매출 보유 %d", total_vc, has_crno, has_revenue)

        # ── Phase 1: 크로스레퍼런스 ──
        phase1_matched = 0
        if not phase2_only:
            if force:
                # force 모드: 기존 매출 데이터 초기화 후 재실행
                await session.execute(
                    update(VcCompany).where(VcCompany.revenue.isnot(None)).values(revenue=None, revenue_year=None)
                )
                await session.commit()
                logger.info("[Phase 1] force 모드: 기존 매출 데이터 초기화 완료")
            phase1_matched = await phase1_cross_reference(session)

        if phase1_only:
            # Phase 1 결과 출력 후 종료
            new_has_revenue = (
                await session.execute(
                    select(func.count()).select_from(VcCompany).where(VcCompany.revenue.isnot(None))
                )
            ).scalar() or 0
            await engine.dispose()
            print(f"\n[Phase 1 완료] 크로스레퍼런스 매칭: {phase1_matched:,}건")
            print(f"  매출 보유 기업: {has_revenue:,} → {new_has_revenue:,}건")
            return

        # ── Phase 2: API 직접 호출 ──
        api_key = settings.DATA_GO_KR_API_KEY
        if not api_key:
            logger.error("DATA_GO_KR_API_KEY가 설정되지 않았습니다. Phase 2 스킵.")
            await engine.dispose()
            return

        primary_year = str(year)
        fallback_year = str(year - 1)

        # Phase 2 대상: corp_reg_no 있고 revenue 없는 기업
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
            logger.info("[Phase 2] 추가 수집 대상 없음 (Phase 1에서 모두 매칭됨).")
        else:
            logger.info("[Phase 2] API 수집 대상: %d건 (limit=%d)", len(companies), limit)

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
                        "  배치 %d~%d (%d건)",
                        i,
                        min(i + batch_size, len(companies)),
                        len(batch),
                    )

                    success, api_calls, minute_start, minute_calls = await phase2_api_batch(
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
                        "  배치 완료: 성공 %d건, API %d회 (누적 %d/%d)",
                        success,
                        api_calls,
                        total_api_calls,
                        len(companies),
                    )

        # ── 최종 리포트 ──
        final_revenue = (
            await session.execute(
                select(func.count()).select_from(VcCompany).where(VcCompany.revenue.isnot(None))
            )
        ).scalar() or 0

    await engine.dispose()

    print("\n" + "=" * 60)
    print("  VcCompany 매출 시딩 완료 리포트")
    print("=" * 60)
    print(f"  전체 VcCompany: {total_vc:,}건")
    print(f"  법인등록번호 보유: {has_crno:,}건")
    print(f"  Phase 1 크로스레퍼런스: {phase1_matched:,}건")
    if not phase1_only and companies:
        print(f"  Phase 2 API 수집 대상: {len(companies):,}건")
        print(f"  Phase 2 수집 성공: {total_success:,}건")
        print(f"  Phase 2 API 호출: {total_api_calls:,}건")
    print(f"  매출 보유 기업: {has_revenue:,} → {final_revenue:,}건")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VcCompany 매출 데이터 하이브리드 시딩")
    parser.add_argument("--limit", type=int, default=9000, help="Phase 2 최대 API 호출 건수 (기본: 9000)")
    parser.add_argument("--year", type=int, default=2024, help="조회 사업연도 (기본: 2024)")
    parser.add_argument("--force", action="store_true", help="기존 매출 데이터 초기화 후 재실행")
    parser.add_argument("--phase1-only", action="store_true", help="Phase 1 (크로스레퍼런스)만 실행")
    parser.add_argument("--phase2-only", action="store_true", help="Phase 2 (API 호출)만 실행")
    args = parser.parse_args()

    asyncio.run(
        main(
            limit=args.limit,
            year=args.year,
            force=args.force,
            phase1_only=args.phase1_only,
            phase2_only=args.phase2_only,
        )
    )
```

**Step 7: ruff 검증**

Run: `cd deal-mgmt && python -m ruff check scripts/seed_vc_revenue_data.py && python -m ruff format --check scripts/seed_vc_revenue_data.py`
Expected: 0건 에러

**Step 8: Phase 1 테스트 실행 (프로덕션 서버)**

```bash
ssh -i "ssh/amic-platform-prod_key.pem" azureuser@52.231.69.38 \
  "cd /opt/amic-platform/deal-mgmt && python -m scripts.seed_vc_revenue_data --phase1-only"
```
Expected: 크로스레퍼런스 매칭 건수 출력

**Step 9: 커밋**

```bash
git add deal-mgmt/scripts/seed_vc_revenue_data.py
git commit -m "feat(deal-mgmt): VcCompany 매출 하이브리드 시딩 스크립트 추가"
```

---

## 실행 순서 요약

1. 스크립트 작성 → ruff 검증
2. 프로덕션 서버에 배포 (git push → CI/CD)
3. `--phase1-only`로 크로스레퍼런스 먼저 실행
4. 결과 확인 후 `--phase2-only`로 API 수집 실행 (시간 소요)
