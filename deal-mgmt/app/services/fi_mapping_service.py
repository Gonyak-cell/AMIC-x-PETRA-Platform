"""FI(금융투자자) 자동 매핑 서비스 — GP 프로필 기반 Tier 분류.

기존 pef_registry.py 라우터 내 _match_gps 로직을 서비스로 추출하고,
GpProfile 기반 Tier 1/2 분류를 추가한다.

Tier 1: 최소기준점(약정 분담 하한) 통과 + 포트폴리오 키워드 매칭
Tier 2: 최소기준점 통과만 or GP 프로필 없음
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gp_profile import GpProfile
from app.models.pef_fund_registry import PefFundRegistry
from app.schemas.pef_registry import (
    FIRecommendationV2,
    GpProfileOut,
    PefFundOut,
)

logger = logging.getLogger(__name__)

# GP명 정규화 접두사 — startswith로 제거
_STRIP_PREFIXES = ["(주)", "주식회사", "(유)", "유한책임회사", "유한회사"]

# GP명 정규화 접미사 — 길이 내림차순 정렬 (긴 접미사 우선 매칭)
_STRIP_SUFFIXES = sorted(
    [
        "자산운용",
        "투자자문",
        "인베스트먼트",
        "캐피탈",
        "캐피털",
        "파트너스",
        "어드바이저스",
        "어드바이저리",
        "어드바이저",
        "투자증권",
        "증권",
        "투자",
        "프라이빗에쿼티",
        "벤처스",
        "에셋매니지먼트",
        "에셋",
    ],
    key=len,
    reverse=True,
)

# GP 프로필 TTL 캐시 (1시간)
_gp_cache: dict[str, GpProfile] | None = None
_gp_cache_ts: float = 0.0
_GP_CACHE_TTL: float = 3600.0
_gp_cache_lock = asyncio.Lock()


def normalize_gp_name(name: str) -> str:
    """GP명 정규화 — PefFundRegistry gp1/gp2/gp3와 GpProfile 매칭용.

    endswith()로 접미사만 제거하여 중간 문자열 오매칭을 방지한다.
    (예: "한국자산신탁" → "한국자산신탁", "자산"이 중간에 있어도 변경 없음)
    """
    n = name.strip()
    # 접두사 제거 (startswith)
    for prefix in _STRIP_PREFIXES:
        if n.startswith(prefix):
            n = n[len(prefix) :]
            break
    # 접미사 제거 (endswith, 반복)
    changed = True
    while changed:
        changed = False
        for suffix in _STRIP_SUFFIXES:
            if n.endswith(suffix):
                n = n[: -len(suffix)]
                changed = True
                break  # 가장 긴 접미사부터 다시 시도
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _format_billions(value: Decimal) -> str:
    """억원 단위 → 읽기 쉬운 한국어 포맷."""
    if value >= 10000:
        return f"{value / Decimal('10000'):.1f}조"
    return f"{value:,.0f}억"


async def _load_gp_profiles(db: AsyncSession) -> dict[str, GpProfile]:
    """GP 프로필 전체 로드 → {normalized_name: GpProfile} 딕셔너리.

    모듈 레벨 TTL 캐시 (1시간)로 매 요청마다 DB 접근을 방지한다.
    asyncio.Lock으로 동시 요청 시 TOCTOU 레이스를 방지한다.
    """
    global _gp_cache, _gp_cache_ts
    now = time.monotonic()
    if _gp_cache is not None and (now - _gp_cache_ts) < _GP_CACHE_TTL:
        return _gp_cache
    async with _gp_cache_lock:
        # double-check after lock acquisition
        now = time.monotonic()
        if _gp_cache is not None and (now - _gp_cache_ts) < _GP_CACHE_TTL:
            return _gp_cache
        result = await db.execute(select(GpProfile))
        profiles = result.scalars().all()
        cache: dict[str, GpProfile] = {}
        for p in profiles:
            db.expunge(p)  # 세션에서 분리 → commit/close 시 expired 방지
            if p.normalized_name in cache:
                logger.warning(
                    "중복 normalized_name=%s (raw=%s vs %s)",
                    p.normalized_name,
                    p.raw_name,
                    cache[p.normalized_name].raw_name,
                )
            cache[p.normalized_name] = p  # last-write-wins: DB 순서 기준 최신 레코드 우선
        _gp_cache = cache
        if not profiles:
            logger.warning("GP 프로필 0건 — 60초 후 재조회")
            _gp_cache_ts = now - _GP_CACHE_TTL + 60.0
        else:
            _gp_cache_ts = now
        return _gp_cache


def _strip_paren(s: str) -> str:
    """괄호와 그 내용을 제거하고 소문자로 변환."""
    return re.sub(r"\s*\([^)]*\)\s*", "", s).strip().lower()


def parse_industry_keywords(raw: str) -> list[str]:
    """산업 키워드 문자열을 `,`와 `/`로 분리하여 리스트로 반환."""
    result: list[str] = []
    for seg in raw.split(","):
        for sub in seg.split("/"):
            kw = sub.strip()
            if kw:
                result.append(kw)
    return result


def _check_keyword_match(
    profile: GpProfile,
    target_keywords: list[str] | None,
) -> bool:
    """GP 포트폴리오 키워드와 타겟 키워드 교집합 확인."""
    if not target_keywords or not profile.portfolio_sectors:
        return False

    profile_sectors = {_strip_paren(s) for s in profile.portfolio_sectors if s}
    target_set = {_strip_paren(kw) for kw in target_keywords if kw}
    return bool(profile_sectors & target_set)


async def recommend_fi(
    db: AsyncSession,
    pefs: list[PefFundRegistry],
    target_amount: Decimal,
    lower_multiplier: Decimal,
    upper_multiplier: Decimal,
    target_keywords: list[str] | None = None,
    limit: int = 50,
) -> list[FIRecommendationV2]:
    """GP 프로필 기반 FI 자동 매핑 v2.

    Args:
        db: DB 세션
        pefs: 필터링된 PEF 목록 (날짜/프로젝트 펀드 필터 적용 후)
        target_amount: 거래금액 (억원)
        lower_multiplier: 하한 배수
        upper_multiplier: 상한 배수
        target_keywords: 산업 키워드 리스트 (Tier 1 판정용, 선택)
        limit: 최대 반환 건수

    Returns:
        Tier → min_fund_size 정렬된 FI 추천 리스트
    """
    logger.info(
        "FI 추천 시작: target=%s억, pefs=%d건, lower=×%.1f, upper=×%.1f",
        target_amount,
        len(pefs),
        lower_multiplier,
        upper_multiplier,
    )
    _start_time = time.monotonic()
    lower_bound = target_amount * lower_multiplier
    upper_bound = target_amount * upper_multiplier

    # 1. GP 프로필 로드
    gp_profiles = await _load_gp_profiles(db)
    logger.debug("GP 프로필 %d개 로드", len(gp_profiles))

    # 2. GP별 PEF 그룹핑
    gp_map: dict[str, list[PefFundRegistry]] = defaultdict(list)
    for pef in pefs:
        for gp in filter(None, [pef.gp1, pef.gp2, pef.gp3]):
            gp_name = gp.strip()
            if gp_name:
                gp_map[gp_name].append(pef)

    # 3. GP별 매칭 + Tier 분류
    recommendations: list[FIRecommendationV2] = []

    for gp_name, funds in gp_map.items():
        # 펀드 중복 제거
        seen_ids: set[uuid.UUID] = set()
        unique_raw: list[PefFundRegistry] = []
        unique_capitals: list[Decimal] = []
        for f in funds:
            if f.id not in seen_ids:
                seen_ids.add(f.id)
                unique_raw.append(f)
                if f.total_committed_capital and f.total_committed_capital > 0:
                    unique_capitals.append(f.total_committed_capital)

        if not unique_capitals:
            continue

        min_size = min(unique_capitals)

        # 범위 매칭 (기존 로직)
        if not (lower_bound <= min_size <= upper_bound):
            continue

        # GP 프로필 조회
        normalized = normalize_gp_name(gp_name)
        profile = gp_profiles.get(normalized)

        # Tier 분류
        tier = 2  # 기본
        tier_reason = ""

        if profile:
            # 최소기준점 체크 (약정 분담 하한)
            threshold_pass = True
            if profile.min_threshold is not None and profile.min_threshold > 0:
                threshold_pass = target_amount >= profile.min_threshold
                if not threshold_pass:
                    tier_reason = f" (최소기준점 {_format_billions(profile.min_threshold)} 미달)"

            if threshold_pass:
                # 키워드 매칭 → Tier 1
                if _check_keyword_match(profile, target_keywords):
                    tier = 1
                    tier_reason = " + 포트폴리오 키워드 매칭"

        total_sum = sum(unique_capitals)
        match_reason = (
            f"Tier {tier} | "
            f"최소 펀드 약정총액 {_format_billions(min_size)} "
            f"(2021년 이후 결성, 펀드 {len(unique_capitals)}건"
            f"{tier_reason})"
        )

        gp_profile_out = None
        if profile:
            gp_profile_out = GpProfileOut.model_validate(profile)

        recommendations.append(
            FIRecommendationV2(
                gp_name=gp_name,
                gp_profile=gp_profile_out,
                tier=tier,
                min_fund_size=min_size,
                matching_funds=[PefFundOut.model_validate(f) for f in unique_raw],
                total_committed_sum=total_sum,
                fund_count=len(unique_capitals),
                match_reason=match_reason,
            )
        )

    # 4. 정렬: Tier ASC → min_fund_size DESC
    recommendations.sort(key=lambda r: (r.tier, -r.min_fund_size))
    result = recommendations[:limit]
    elapsed = time.monotonic() - _start_time
    logger.info(
        "FI 추천 완료: target=%s억, matched_gps=%d, total_funds=%d, elapsed=%.2fs",
        target_amount,
        len(result),
        sum(r.fund_count for r in result),
        elapsed,
    )
    return result
