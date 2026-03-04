"""FI 자동 매핑 v2 — GP 프로필 기반 Tier 분류 테스트.

Tier 분류 알고리즘 검증:
  - Tier 1: GP 프로필 존재 + 최소기준점 통과 + 포트폴리오 키워드 매칭
  - Tier 2: GP 프로필 존재 + 최소기준점 통과 (키워드 미매칭 또는 미제공)
  - Tier 2 fallback: GP 프로필 없음 → 기존 range matching만 적용
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gp_profile import GpProfile
from app.models.pef_fund_registry import PefFundRegistry
from app.services.fi_mapping_service import normalize_gp_name

# ── 헬퍼 ─────────────────────────────────────────────────────


async def _create_txn(
    client: AsyncClient,
    deal_value: int | None,
) -> str:
    """deal_value(억원)를 지정하여 Transaction을 생성하고 ID를 반환한다."""
    payload: dict = {
        "name": "FI v2 매핑 테스트",
        "code_name": f"FIV2-TEST-{uuid.uuid4().hex[:8]}",
        "target_company_name": "V2테스트타깃",
        "client_name": "V2테스트고객",
        "side": "SELL",
        "lead_advisor_email": "test@example.com",
    }
    if deal_value is not None:
        payload["estimated_deal_value"] = deal_value
    resp = await client.post("/api/v1/transactions", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _seed_pefs(async_session: AsyncSession, pefs: list[dict]) -> None:
    """테스트용 PEF 레코드를 DB에 직접 삽입한다."""
    for data in pefs:
        pef = PefFundRegistry(
            id=data.get("id", uuid.uuid4()),
            pef_name=data["pef_name"],
            registration_date=data.get("registration_date"),
            gp1=data.get("gp1"),
            gp2=data.get("gp2"),
            gp3=data.get("gp3"),
            total_committed_capital=data.get("total_committed_capital"),
        )
        async_session.add(pef)
    await async_session.commit()


async def _seed_gp_profiles(async_session: AsyncSession, profiles: list[dict]) -> None:
    """테스트용 GP 프로필을 DB에 삽입한다."""
    for data in profiles:
        profile = GpProfile(
            raw_name=data["raw_name"],
            normalized_name=data["normalized_name"],
            min_threshold=data.get("min_threshold"),
            portfolio_sectors=data.get("portfolio_sectors"),
            portfolio_companies=data.get("portfolio_companies"),
            recent_pef_count=data.get("recent_pef_count"),
            total_pef_count=data.get("total_pef_count"),
            min_committed_capital=data.get("min_committed_capital"),
            max_committed_capital=data.get("max_committed_capital"),
        )
        async_session.add(profile)
    await async_session.commit()


def _fi_url(txn_id: str, **params: object) -> str:
    """FI 추천 API URL을 구성한다."""
    base = f"/api/v1/transactions/{txn_id}/fi-recommendations"
    if not params:
        return base
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{qs}"


# ══════════════════════════════════════════════════════════
# Unit Tests: normalize_gp_name
# ══════════════════════════════════════════════════════════


class TestNormalizeGpName:
    """GP명 정규화 함수 단위 테스트."""

    def test_mid_string_safety(self) -> None:
        """중간에 접미사 문자열이 포함된 이름은 변경되지 않는다 (CRIT-03)."""
        # "자산신탁" 안에 "자산"이 포함되어도 endswith가 아니므로 안전
        assert normalize_gp_name("한국자산신탁") == "한국자산신탁"
        # "투자은행" 안에 "투자"가 포함되어도 endswith가 아니므로 안전
        assert normalize_gp_name("한국투자은행") == "한국투자은행"

    def test_strip_asset_management_suffix(self) -> None:
        """'자산운용' 접미사가 제거된다."""
        assert normalize_gp_name("알파자산운용") == "알파"

    def test_strip_investment_advisory_suffix(self) -> None:
        """'투자자문' 접미사가 제거된다."""
        assert normalize_gp_name("베타투자자문") == "베타"

    def test_strip_investment_suffix(self) -> None:
        """'인베스트먼트' 접미사가 제거된다."""
        assert normalize_gp_name("감마인베스트먼트") == "감마"

    def test_strip_company_prefix(self) -> None:
        """'(주)' 접두사가 제거된다."""
        assert normalize_gp_name("(주)델타캐피탈") == "델타"

    def test_strip_capital_suffix(self) -> None:
        """'캐피탈' 접미사가 제거된다."""
        assert normalize_gp_name("델타캐피탈") == "델타"

    def test_strip_multiple_suffixes(self) -> None:
        """복합 접미사도 순차적으로 모두 제거된다."""
        assert normalize_gp_name("(주)엡실론자산운용") == "엡실론"

    def test_whitespace_normalization(self) -> None:
        """연속 공백은 단일 공백으로 정규화된다."""
        assert normalize_gp_name("  알파   베타  ") == "알파 베타"

    def test_plain_name_unchanged(self) -> None:
        """접미사가 없는 이름은 그대로 반환된다."""
        assert normalize_gp_name("맥쿼리") == "맥쿼리"

    def test_strip_advisors_before_advisor(self) -> None:
        """'어드바이저스'가 '어드바이저'보다 먼저 제거된다 (길이 내림차순)."""
        assert normalize_gp_name("알파어드바이저스") == "알파"

    def test_strip_partners_suffix(self) -> None:
        """'파트너스' 접미사가 제거된다."""
        assert normalize_gp_name("베타파트너스") == "베타"

    def test_strip_capital_tyeol_suffix(self) -> None:
        """'캐피털' 접미사가 제거된다 (캐피탈과 별개)."""
        assert normalize_gp_name("감마캐피털") == "감마"


# ══════════════════════════════════════════════════════════
# Integration Tests: Tier 분류
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_tier2_when_no_gp_profile(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """GP 프로필이 없으면 Tier 2로 분류된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "무프로필GP펀드1호",
                "registration_date": "2022-01-01",
                "gp1": "무프로필GP",
                "total_committed_capital": 1500,
            },
        ],
    )
    # GP 프로필 시딩 안 함 → 프로필 없음

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    rec = recs[0]
    assert rec["tier"] == 2
    assert rec["gp_profile"] is None


@pytest.mark.asyncio
async def test_tier2_with_profile_no_keywords(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """GP 프로필 있지만 target_keywords 미제공 시 Tier 2."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "프로필GP펀드1호",
                "registration_date": "2022-01-01",
                "gp1": "알파자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "알파자산운용",
                "normalized_name": "알파",
                "min_threshold": 500,
                "portfolio_sectors": ["IT", "헬스케어"],
            },
        ],
    )

    # target_keywords 미제공
    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    rec = recs[0]
    assert rec["tier"] == 2
    assert rec["gp_profile"] is not None
    assert rec["gp_profile"]["raw_name"] == "알파자산운용"


@pytest.mark.asyncio
async def test_tier1_with_keyword_match(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """GP 프로필 + 최소기준점 통과 + 키워드 매칭 → Tier 1."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "헬스GP펀드1호",
                "registration_date": "2022-01-01",
                "gp1": "헬스자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "헬스자산운용",
                "normalized_name": "헬스",
                "min_threshold": 500,
                "portfolio_sectors": ["헬스케어", "바이오"],
            },
        ],
    )

    # target_keywords에 "헬스케어" 포함 → 매칭
    resp = await client.get(_fi_url(txn_id, target_keywords="헬스케어,IT"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert recs[0]["tier"] == 1
    assert "키워드" in recs[0]["match_reason"]


@pytest.mark.asyncio
async def test_tier2_keyword_no_match(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """GP 프로필 + 최소기준점 통과 + 키워드 불일치 → Tier 2."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "유통GP펀드1호",
                "registration_date": "2022-01-01",
                "gp1": "유통인베스트먼트",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "유통인베스트먼트",
                "normalized_name": "유통",
                "min_threshold": 500,
                "portfolio_sectors": ["유통", "소비재"],
            },
        ],
    )

    # target_keywords에 GP 투자분야와 겹치는 것 없음
    resp = await client.get(_fi_url(txn_id, target_keywords="반도체,자동차"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert recs[0]["tier"] == 2


@pytest.mark.asyncio
async def test_threshold_fail_demotes_tier(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """최소기준점 미달 시 키워드 매칭 여부와 무관하게 Tier 2 + 미달 이유 표시."""
    txn_id = await _create_txn(client, 300)  # target=300억, min_threshold=500
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "기준미달GP펀드1호",
                "registration_date": "2022-01-01",
                "gp1": "기준미달GP",
                "total_committed_capital": 200,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "기준미달GP",
                "normalized_name": "기준미달GP",
                "min_threshold": 500,
                "portfolio_sectors": ["반도체"],
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id, lower_multiplier="0.1", upper_multiplier="5.0", target_keywords="반도체"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert recs[0]["tier"] == 2
    assert "미달" in recs[0]["match_reason"]


@pytest.mark.asyncio
async def test_tier_sorting_tier_asc_then_size_desc(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Tier ASC → min_fund_size DESC 정렬 검증."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            # Tier 1 GP: 키워드 매칭
            {
                "pef_name": "T1소형펀드",
                "registration_date": "2022-01-01",
                "gp1": "T1소형GP자산운용",
                "total_committed_capital": 800,
            },
            {
                "pef_name": "T1대형펀드",
                "registration_date": "2022-01-01",
                "gp1": "T1대형GP자산운용",
                "total_committed_capital": 2000,
            },
            # Tier 2 GP: 프로필 없음
            {
                "pef_name": "T2초대형펀드",
                "registration_date": "2022-01-01",
                "gp1": "T2초대형GP",
                "total_committed_capital": 2500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "T1소형GP자산운용",
                "normalized_name": "T1소형GP",
                "min_threshold": 500,
                "portfolio_sectors": ["IT"],
            },
            {
                "raw_name": "T1대형GP자산운용",
                "normalized_name": "T1대형GP",
                "min_threshold": 500,
                "portfolio_sectors": ["IT"],
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id, target_keywords="IT"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 3

    # Tier 1 → Tier 2 순서
    assert recs[0]["tier"] == 1
    assert recs[1]["tier"] == 1
    assert recs[2]["tier"] == 2

    # Tier 1 내부: min_fund_size 내림차순
    assert float(recs[0]["min_fund_size"]) >= float(recs[1]["min_fund_size"])


@pytest.mark.asyncio
async def test_gp_profile_fields_in_response(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """응답에 GP 프로필 필드가 포함된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "필드확인GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "필드확인자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "필드확인자산운용",
                "normalized_name": "필드확인",
                "min_threshold": 300,
                "portfolio_sectors": ["에너지", "인프라"],
                "portfolio_companies": ["한국전력", "SK이노베이션"],
                "recent_pef_count": 3,
                "total_pef_count": 7,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    profile = recs[0]["gp_profile"]
    assert profile is not None
    assert profile["raw_name"] == "필드확인자산운용"
    assert float(profile["min_threshold"]) == 300.0
    assert profile["portfolio_sectors"] == ["에너지", "인프라"]
    assert profile["portfolio_companies"] == ["한국전력", "SK이노베이션"]
    assert profile["recent_pef_count"] == 3
    assert profile["total_pef_count"] == 7


@pytest.mark.asyncio
async def test_v2_response_has_tier_field(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """v2 응답에 tier 필드가 존재한다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "V2필드확인펀드",
                "registration_date": "2022-01-01",
                "gp1": "V2필드확인GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert "tier" in recs[0]
    assert "gp_profile" in recs[0]
    # 기존 v1 필드 유지 확인
    assert "gp_name" in recs[0]
    assert "min_fund_size" in recs[0]
    assert "matching_funds" in recs[0]
    assert "total_committed_sum" in recs[0]
    assert "fund_count" in recs[0]
    assert "match_reason" in recs[0]


@pytest.mark.asyncio
async def test_match_reason_includes_tier_info(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """match_reason에 Tier 정보가 포함된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "이유확인GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "이유확인GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    reason = recs[0]["match_reason"]
    assert "Tier" in reason


@pytest.mark.asyncio
async def test_target_keywords_parsing(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """target_keywords 쿼리 파라미터가 쉼표로 파싱된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "파싱GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "파싱테스트자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "파싱테스트자산운용",
                "normalized_name": "파싱테스트",
                "min_threshold": 500,
                "portfolio_sectors": ["반도체"],
            },
        ],
    )

    # 쉼표+공백이 포함된 키워드
    resp = await client.get(_fi_url(txn_id, target_keywords="반도체, 디스플레이, IT"))
    assert resp.status_code == 200
    recs = resp.json()

    # "반도체"가 매칭 → Tier 1
    assert len(recs) == 1
    assert recs[0]["tier"] == 1


@pytest.mark.asyncio
async def test_keyword_match_case_insensitive(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """키워드 매칭이 대소문자 무시로 동작한다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "대소문자GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "케이스테스트자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "케이스테스트자산운용",
                "normalized_name": "케이스테스트",
                "min_threshold": 500,
                "portfolio_sectors": ["IT서비스"],
            },
        ],
    )

    # 대문자로 검색
    resp = await client.get(_fi_url(txn_id, target_keywords="it서비스"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert recs[0]["tier"] == 1


@pytest.mark.asyncio
async def test_threshold_none_treated_as_pass(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """min_threshold가 None인 GP 프로필은 최소기준점 통과로 취급."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "임계없음GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "임계없음자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "임계없음자산운용",
                "normalized_name": "임계없음",
                "min_threshold": None,  # 기준점 없음
                "portfolio_sectors": ["바이오"],
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id, target_keywords="바이오"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert recs[0]["tier"] == 1  # 기준점 없음 → 통과 → 키워드 매칭 → Tier 1


@pytest.mark.asyncio
async def test_multiple_gps_mixed_tiers(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """여러 GP가 혼합 Tier로 분류되는 통합 시나리오."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "GP_A_펀드",
                "registration_date": "2022-01-01",
                "gp1": "GP_A자산운용",
                "total_committed_capital": 1000,
            },
            {
                "pef_name": "GP_B_펀드",
                "registration_date": "2022-01-01",
                "gp1": "GP_B투자자문",
                "total_committed_capital": 1200,
            },
            {
                "pef_name": "GP_C_펀드",
                "registration_date": "2022-01-01",
                "gp1": "GP_C_캐피탈",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "GP_A자산운용",
                "normalized_name": "GP_A",
                "min_threshold": 500,
                "portfolio_sectors": ["반도체"],  # 키워드 매칭 O
            },
            {
                "raw_name": "GP_B투자자문",
                "normalized_name": "GP_B",
                "min_threshold": 500,
                "portfolio_sectors": ["제약"],  # 키워드 매칭 X
            },
            # GP_C: 프로필 없음
        ],
    )

    resp = await client.get(_fi_url(txn_id, target_keywords="반도체"))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 3
    gp_tier = {r["gp_name"]: r["tier"] for r in recs}
    assert gp_tier["GP_A자산운용"] == 1  # 프로필 + 키워드 매칭
    assert gp_tier["GP_B투자자문"] == 2  # 프로필 있지만 키워드 불일치
    assert gp_tier["GP_C_캐피탈"] == 2  # 프로필 없음 → fallback


@pytest.mark.asyncio
async def test_empty_target_keywords_treated_as_none(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """target_keywords='' 빈 문자열은 키워드 미제공과 동일하게 처리."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "빈키워드GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "빈키워드자산운용",
                "total_committed_capital": 1500,
            },
        ],
    )
    await _seed_gp_profiles(
        async_session,
        [
            {
                "raw_name": "빈키워드자산운용",
                "normalized_name": "빈키워드",
                "min_threshold": 500,
                "portfolio_sectors": ["IT"],
            },
        ],
    )

    # 빈 문자열 target_keywords → 키워드 매칭 불가 → Tier 2
    resp = await client.get(_fi_url(txn_id, target_keywords=""))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    assert recs[0]["tier"] == 2


@pytest.mark.asyncio
async def test_v2_backward_compat_existing_fields(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """v2 응답이 기존 v1 필드를 모두 유지한다 (하위 호환)."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "호환성테스트펀드",
                "registration_date": "2022-01-01",
                "gp1": "호환성GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    rec = recs[0]
    # v1 필드 전체 검증
    assert isinstance(rec["gp_name"], str)
    assert isinstance(rec["min_fund_size"], (int, float))
    assert isinstance(rec["matching_funds"], list)
    assert isinstance(rec["total_committed_sum"], (int, float))
    assert isinstance(rec["fund_count"], int)
    assert isinstance(rec["match_reason"], str)
    # v2 추가 필드
    assert isinstance(rec["tier"], int)
    assert "gp_profile" in rec  # None 또는 dict


# ══════════════════════════════════════════════════════════
# Error Path Tests: 429 Rate Limit, 404 Not Found
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fi_recommendations_404_invalid_txn(
    client: AsyncClient,
) -> None:
    """존재하지 않는 트랜잭션 ID → 404."""
    fake_txn_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/transactions/{fake_txn_id}/fi-recommendations")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fi_recommendations_429_rate_limit(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """FI 추천 API rate limit 초과 시 429 응답."""
    from app.core.rate_limiter import fi_rate_limiter

    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "레이트GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "레이트GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    # rate limiter 한도를 0으로 설정 → 즉시 429
    original_max = fi_rate_limiter._max_calls
    fi_rate_limiter._max_calls = 0
    try:
        resp = await client.get(f"/api/v1/transactions/{txn_id}/fi-recommendations")
        assert resp.status_code == 429
    finally:
        fi_rate_limiter._max_calls = original_max


# ══════════════════════════════════════════════════════════
# Boundary Value Tests
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fi_recommendations_zero_deal_value(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """deal_value=0 이면 range matching이 0범위 → 빈 결과 가능."""
    txn_id = await _create_txn(client, 0)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "경계값GP펀드",
                "registration_date": "2022-01-01",
                "gp1": "경계값GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    # deal_value=0 → 매칭 범위가 0 → 결과 없을 수 있음
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_fi_recommendations_limit_one(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """limit=1 파라미터로 결과 1건만 반환."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "리밋A펀드",
                "registration_date": "2022-01-01",
                "gp1": "리밋A자산운용",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "리밋B펀드",
                "registration_date": "2022-01-01",
                "gp1": "리밋B자산운용",
                "total_committed_capital": 2000,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id, limit=1))
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) <= 1
