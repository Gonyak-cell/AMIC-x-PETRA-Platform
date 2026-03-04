"""VcCompany 매출액 교차 참조 — 4-Tier 계층적 매칭.

SICompany 테이블의 revenue 데이터를 VcCompany에 복사한다.
매칭 전략 (우선순위):
  Tier 1: 회사명 정확 일치 (strip only)
  Tier 2: 법인등록번호 매칭 (jurir_no ↔ corp_reg_no)
  Tier 3: 정규화 회사명 일치 (법인격 접두사/접미사 제거 + 공백 제거)
  Tier 4: Fuzzy 매칭 (rapidfuzz token_sort_ratio ≥ 90)

사용법:
    cd deal-mgmt
    python -m scripts.enrich_vc_revenue            # 실행
    python -m scripts.enrich_vc_revenue --dry-run   # 미리보기 (UPDATE 없음)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
from decimal import Decimal

from rapidfuzz import fuzz, process
from sqlalchemy import bindparam, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

# ── 회사명 정규화 ──

_LEGAL_ENTITY_MARKERS = ["주식회사", "유한책임회사", "유한회사", "(주)", "(유)", "(합)"]

_NON_DIGIT_RE = re.compile(r"\D")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """회사명 정규화 — 법인격 표기 제거 + 공백 전체 제거.

    "(주)삼성전자" → "삼성전자"
    "주식회사 LG화학" → "LG화학"
    "삼성전자(주)" → "삼성전자"
    "SK  C&C" → "SKC&C"
    """
    n = name.strip()
    # 접두사 제거 (시작 위치)
    for marker in _LEGAL_ENTITY_MARKERS:
        if n.startswith(marker):
            n = n[len(marker) :]
            break
    # 접미사 제거 (끝 위치)
    for marker in _LEGAL_ENTITY_MARKERS:
        if n.endswith(marker):
            n = n[: -len(marker)]
            break
    # 공백 전체 제거 → 정규화 키
    n = _WHITESPACE_RE.sub("", n)
    return n


def normalize_reg_no(value: str) -> str:
    """등록번호 정규화 — 숫자만 추출."""
    return _NON_DIGIT_RE.sub("", value)


# ── DB 연결 ──


async def _get_engine_and_session() -> tuple:
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


# ── 벌크 UPDATE 헬퍼 ──


async def _flush_batch(
    session: AsyncSession,
    batch: list[dict],
    *,
    dry_run: bool,
) -> None:
    """배치 벌크 UPDATE (Core 테이블 사용)."""
    if not batch or dry_run:
        return
    from app.models.vc_company import VcCompany

    tbl = VcCompany.__table__
    stmt = tbl.update().where(tbl.c.id == bindparam("_vc_id")).values(revenue=bindparam("_revenue_val"))
    await session.execute(stmt, batch)


# ── 메인 로직 ──


async def enrich_from_si_companies(session: AsyncSession, *, dry_run: bool = False) -> dict[str, int]:
    """SICompany.revenue → VcCompany.revenue 4-Tier 계층 매칭."""
    from app.models.si_company import SICompany
    from app.models.vc_company import VcCompany

    # ── 1. SICompany 룩업 테이블 구축 ──
    si_result = await session.execute(
        select(SICompany.company_name, SICompany.revenue, SICompany.jurir_no).where(
            SICompany.revenue.isnot(None),
            SICompany.revenue > 0,
        )
    )

    si_by_name: dict[str, Decimal] = {}  # exact name → revenue (억원)
    si_by_reg: dict[str, Decimal] = {}  # normalized reg_no → revenue
    si_by_normalized: dict[str, tuple[str, Decimal]] = {}  # normalized → (original, revenue)

    for row in si_result:
        raw_name = row[0].strip() if row[0] else None
        if not raw_name or not row[1]:
            continue
        revenue_eok = Decimal(str(row[1])) / Decimal("100000000")

        # Tier 1 lookup
        si_by_name[raw_name] = revenue_eok

        # Tier 2 lookup
        jurir_no = row[2]
        if jurir_no:
            reg = normalize_reg_no(jurir_no)
            if reg:
                si_by_reg[reg] = revenue_eok

        # Tier 3 lookup
        norm = normalize_company_name(raw_name)
        if norm:
            si_by_normalized[norm] = (raw_name, revenue_eok)

    if not si_by_name:
        logger.info("SICompany에 매출 데이터 없음 — 교차참조 스킵")
        return {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0}

    logger.info(
        "SICompany 매출 보유: %d건 (등록번호: %d건, 정규화명: %d건)",
        len(si_by_name),
        len(si_by_reg),
        len(si_by_normalized),
    )

    # ── 2. VcCompany 매출 미보유 기업 조회 ──
    vc_result = await session.execute(
        select(VcCompany.id, VcCompany.company_name, VcCompany.corp_reg_no).where(VcCompany.revenue.is_(None))
    )
    vc_rows = vc_result.all()
    logger.info("VcCompany 매출 미보유: %d건", len(vc_rows))

    # ── 3. Tier 1~3 매칭 ──
    tier_counts = {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0}
    batch_updates: list[dict] = []
    fuzzy_candidates: list[tuple[int, str]] = []  # (id, name) — Tier 4용

    for vc_row in vc_rows:
        vc_id: int = vc_row[0]
        vc_name: str = vc_row[1].strip() if vc_row[1] else ""
        vc_reg: str | None = vc_row[2]

        if not vc_name:
            continue

        revenue: Decimal | None = None
        tier: str = ""

        # Tier 1: exact name
        rev = si_by_name.get(vc_name)
        if rev is not None:
            revenue, tier = rev, "tier1"

        # Tier 2: registration number
        if revenue is None and vc_reg:
            reg = normalize_reg_no(vc_reg)
            if reg:
                rev = si_by_reg.get(reg)
                if rev is not None:
                    revenue, tier = rev, "tier2"

        # Tier 3: normalized name
        if revenue is None:
            norm = normalize_company_name(vc_name)
            if norm:
                match = si_by_normalized.get(norm)
                if match is not None:
                    revenue, tier = match[1], "tier3"

        if revenue is not None:
            tier_counts[tier] += 1
            batch_updates.append({"_vc_id": vc_id, "_revenue_val": revenue})

            if len(batch_updates) >= BATCH_SIZE:
                await _flush_batch(session, batch_updates, dry_run=dry_run)
                batch_updates.clear()
                total = sum(tier_counts.values())
                logger.info("매출 교차참조: %d건 업데이트...", total)
        else:
            fuzzy_candidates.append((vc_id, vc_name))

    # 잔여 배치
    await _flush_batch(session, batch_updates, dry_run=dry_run)
    batch_updates.clear()

    t1_t3_total = sum(tier_counts.values())
    logger.info(
        "Tier 1~3 완료: exact=%d, reg=%d, norm=%d (합계 %d건)",
        tier_counts["tier1"],
        tier_counts["tier2"],
        tier_counts["tier3"],
        t1_t3_total,
    )

    # ── 4. Tier 4: Fuzzy 매칭 ──
    if fuzzy_candidates and si_by_normalized:
        # rapidfuzz 선택지 구축: normalized_name → (original, revenue)
        si_norm_names = list(si_by_normalized.keys())

        logger.info(
            "Tier 4 fuzzy 매칭 시작: %d건 VcCompany × %d건 SICompany", len(fuzzy_candidates), len(si_norm_names)
        )

        for vc_id, vc_name in fuzzy_candidates:
            norm = normalize_company_name(vc_name)
            if not norm or len(norm) < 2:
                continue

            result = process.extractOne(
                norm,
                si_norm_names,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=90,
            )
            if result is not None:
                matched_norm, score, _idx = result
                si_original, revenue = si_by_normalized[matched_norm]
                tier_counts["tier4"] += 1
                batch_updates.append({"_vc_id": vc_id, "_revenue_val": revenue})
                logger.info("  fuzzy: '%s' → '%s' (score=%.1f)", vc_name, si_original, score)

                if len(batch_updates) >= BATCH_SIZE:
                    await _flush_batch(session, batch_updates, dry_run=dry_run)
                    batch_updates.clear()

        # 잔여 배치
        await _flush_batch(session, batch_updates, dry_run=dry_run)

    # ── 5. 커밋 ──
    if not dry_run:
        await session.commit()

    total = sum(tier_counts.values())
    logger.info(
        "매출 교차참조 완료: 합계 %d건 (exact=%d, reg=%d, norm=%d, fuzzy=%d)%s",
        total,
        tier_counts["tier1"],
        tier_counts["tier2"],
        tier_counts["tier3"],
        tier_counts["tier4"],
        " [DRY-RUN]" if dry_run else "",
    )
    return tier_counts


async def main(*, dry_run: bool = False) -> None:
    engine, session_factory = await _get_engine_and_session()
    async with session_factory() as session:
        await enrich_from_si_companies(session, dry_run=dry_run)
    await engine.dispose()
    logger.info("VcCompany 매출 enrichment 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VcCompany 매출 교차참조 (4-Tier)")
    parser.add_argument("--dry-run", action="store_true", help="UPDATE 없이 매칭 결과만 출력")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
