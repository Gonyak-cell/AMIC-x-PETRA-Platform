"""ValueChain(VC) 매핑 테스트 — 1,574 세부 업종 계수표 기반.

검증 범위:
  - VC 데이터 통계 (시딩 상태)
  - 업종명 자동완성 (DISTINCT LIKE)
  - 전방/후방/경쟁 매핑 알고리즘
  - 매출 필터 적용
  - 빈 데이터 graceful degradation
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vc_company import VcCompany
from app.models.vc_industry_coefficient import VcIndustryCoefficient

# ── 헬퍼 ─────────────────────────────────────────────────────


async def _seed_vc_companies(async_session: AsyncSession, companies: list[dict]) -> None:
    """테스트용 VC 기업을 DB에 삽입한다."""
    for data in companies:
        company = VcCompany(
            company_name=data["company_name"],
            industry_name=data["industry_name"],
            io_sector_code=data.get("io_sector_code"),
            io_sector_name=data.get("io_sector_name"),
            corp_type=data.get("corp_type"),
            revenue=data.get("revenue"),
            revenue_year=data.get("revenue_year"),
            listing_code=data.get("listing_code"),
            english_name=data.get("english_name"),
        )
        async_session.add(company)
    await async_session.commit()


async def _seed_vc_coefficients(async_session: AsyncSession, coefficients: list[dict]) -> None:
    """테스트용 업종 계수를 DB에 삽입한다."""
    for data in coefficients:
        coeff = VcIndustryCoefficient(
            source_industry=data["source_industry"],
            target_industry=data["target_industry"],
            coefficient=data["coefficient"],
        )
        async_session.add(coeff)
    await async_session.commit()


# ══════════════════════════════════════════════════════════
# VC 데이터 통계 엔드포인트
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_vc_stats_empty_db(client: AsyncClient) -> None:
    """데이터 없으면 모든 카운트 0 + is_seeded=false."""
    resp = await client.get("/api/v1/si-mapping/vc-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vc_companies_count"] == 0
    assert data["vc_coefficients_count"] == 0
    assert data["revenue_count"] == 0
    assert data["is_seeded"] is False


@pytest.mark.asyncio
async def test_vc_stats_with_data(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """데이터 시딩 후 카운트와 is_seeded 반영."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "A사", "industry_name": "반도체", "revenue": Decimal("500")},
            {"company_name": "B사", "industry_name": "자동차", "revenue": None},
        ],
    )
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "반도체", "target_industry": "자동차", "coefficient": Decimal("0.050")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vc_companies_count"] == 2
    assert data["vc_coefficients_count"] == 1
    assert data["revenue_count"] == 1  # B사 매출 NULL
    assert data["is_seeded"] is True


# ══════════════════════════════════════════════════════════
# 업종명 자동완성 검색
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_industry_search_basic(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """업종명 검색 기본 동작."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "A반도체", "industry_name": "반도체 제조업"},
            {"company_name": "B반도체", "industry_name": "반도체 제조업"},
            {"company_name": "C디스플레이", "industry_name": "디스플레이 제조업"},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/industries/search?q=반도체")
    assert resp.status_code == 200
    results = resp.json()

    assert len(results) == 1
    assert results[0]["industry_name"] == "반도체 제조업"
    assert results[0]["company_count"] == 2


@pytest.mark.asyncio
async def test_industry_search_multiple_matches(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """여러 업종이 검색되면 기업 수 내림차순 정렬."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "A제조", "industry_name": "전자부품 제조업"},
            {"company_name": "B제조", "industry_name": "전자부품 제조업"},
            {"company_name": "C제조", "industry_name": "전자부품 제조업"},
            {"company_name": "D제조", "industry_name": "전기장비 제조업"},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/industries/search?q=제조")
    assert resp.status_code == 200
    results = resp.json()

    assert len(results) == 2
    # 기업 수 내림차순
    assert results[0]["company_count"] >= results[1]["company_count"]


@pytest.mark.asyncio
async def test_industry_search_no_match(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """검색 결과 없으면 빈 배열."""
    await _seed_vc_companies(
        async_session,
        [{"company_name": "A사", "industry_name": "반도체 제조업"}],
    )

    resp = await client.get("/api/v1/si-mapping/industries/search?q=항공우주")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_industry_search_limit(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """limit 파라미터로 결과 수 제한."""
    # 5개 서로 다른 업종
    await _seed_vc_companies(
        async_session,
        [{"company_name": f"기업{i}", "industry_name": f"서비스업{i}"} for i in range(5)],
    )

    resp = await client.get("/api/v1/si-mapping/industries/search?q=서비스&limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ══════════════════════════════════════════════════════════
# ValueChain 매핑 — 전방/후방/경쟁
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_vc_map_forward_chains(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """전방(고객) 체인: source=타겟 → target 업종 계수 내림차순."""
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "반도체", "target_industry": "자동차", "coefficient": Decimal("0.100")},
            {"source_industry": "반도체", "target_industry": "가전", "coefficient": Decimal("0.200")},
            {"source_industry": "반도체", "target_industry": "통신", "coefficient": Decimal("0.050")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200
    data = resp.json()

    assert data["target_industry"] == "반도체"
    assert data["total_forward"] == 3

    # 계수 내림차순
    forward = data["forward_chains"]
    assert forward[0]["industry_name"] == "가전"
    assert forward[1]["industry_name"] == "자동차"
    assert forward[2]["industry_name"] == "통신"


@pytest.mark.asyncio
async def test_vc_map_backward_chains(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """후방(공급) 체인: target=타겟 → source 업종 계수 내림차순."""
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "화학", "target_industry": "반도체", "coefficient": Decimal("0.150")},
            {"source_industry": "전력", "target_industry": "반도체", "coefficient": Decimal("0.080")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_backward"] == 2

    backward = data["backward_chains"]
    assert backward[0]["industry_name"] == "화학"
    assert backward[1]["industry_name"] == "전력"


@pytest.mark.asyncio
async def test_vc_map_excludes_self_loop(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """자기 자신 업종(self-loop)은 전방/후방에서 제외된다."""
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "반도체", "target_industry": "반도체", "coefficient": Decimal("0.500")},
            {"source_industry": "반도체", "target_industry": "자동차", "coefficient": Decimal("0.100")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200
    data = resp.json()

    # 전방에서 자기 자신 제외
    forward_names = [c["industry_name"] for c in data["forward_chains"]]
    assert "반도체" not in forward_names
    assert "자동차" in forward_names


@pytest.mark.asyncio
async def test_vc_map_competitors(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """경쟁사: 같은 업종 + 매출 100억↑ + 내림차순."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "대형반도체A", "industry_name": "반도체", "revenue": Decimal("5000")},
            {"company_name": "중형반도체B", "industry_name": "반도체", "revenue": Decimal("300")},
            {"company_name": "소형반도체C", "industry_name": "반도체", "revenue": Decimal("50")},
            {"company_name": "기타업종D", "industry_name": "자동차", "revenue": Decimal("1000")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200
    data = resp.json()

    # 매출 100억 이상만 포함 (C=50은 제외, D=자동차 업종 제외)
    assert data["total_competitors"] == 2
    competitors = data["competitors"]
    names = [c["company_name"] for c in competitors]
    assert "대형반도체A" in names
    assert "중형반도체B" in names
    assert "소형반도체C" not in names
    assert "기타업종D" not in names

    # 매출 내림차순
    assert competitors[0]["company_name"] == "대형반도체A"
    assert competitors[1]["company_name"] == "중형반도체B"


@pytest.mark.asyncio
async def test_vc_map_custom_min_revenue(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """min_revenue 파라미터로 매출 기준 변경."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "A사", "industry_name": "반도체", "revenue": Decimal("500")},
            {"company_name": "B사", "industry_name": "반도체", "revenue": Decimal("30")},
        ],
    )

    # min_revenue=0 → 매출 있는 기업 전부
    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체&min_revenue=0")
    assert resp.status_code == 200
    assert resp.json()["total_competitors"] == 2

    # min_revenue=100 (기본) → A사만
    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체&min_revenue=100")
    assert resp.status_code == 200
    assert resp.json()["total_competitors"] == 1


@pytest.mark.asyncio
async def test_vc_map_top_n_limit(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """top_n 파라미터로 각 카테고리 결과 수 제한."""
    # 전방 계수 5개
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "반도체", "target_industry": f"업종{i}", "coefficient": Decimal(f"0.{10 - i:03d}")}
            for i in range(5)
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체&top_n=3")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_forward"] == 3


@pytest.mark.asyncio
async def test_vc_map_companies_in_chain_panels(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """전방/후방 패널에 해당 업종 기업이 포함된다."""
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "반도체", "target_industry": "자동차", "coefficient": Decimal("0.100")},
        ],
    )
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "현대차", "industry_name": "자동차", "revenue": Decimal("500")},
            {"company_name": "기아", "industry_name": "자동차", "revenue": Decimal("300")},
            {"company_name": "테슬라", "industry_name": "자동차", "revenue": Decimal("50")},  # 100억 미만
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200
    data = resp.json()

    forward = data["forward_chains"]
    assert len(forward) == 1
    panel = forward[0]
    assert panel["industry_name"] == "자동차"

    # 매출 100억↑ 기업만 포함
    company_names = [c["company_name"] for c in panel["companies"]]
    assert "현대차" in company_names
    assert "기아" in company_names
    assert "테슬라" not in company_names


@pytest.mark.asyncio
async def test_vc_map_empty_coefficients(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """계수 데이터 없으면 빈 체인 반환 (graceful degradation)."""
    resp = await client.get("/api/v1/si-mapping/vc-map?industry=존재안하는업종")
    assert resp.status_code == 200
    data = resp.json()

    assert data["target_industry"] == "존재안하는업종"
    assert data["forward_chains"] == []
    assert data["backward_chains"] == []
    assert data["competitors"] == []
    assert data["total_forward"] == 0
    assert data["total_backward"] == 0
    assert data["total_competitors"] == 0


@pytest.mark.asyncio
async def test_vc_map_competitors_null_revenue_excluded(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """매출(revenue)이 NULL인 기업은 경쟁사에서 제외."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "매출있음A", "industry_name": "반도체", "revenue": Decimal("200")},
            {"company_name": "매출없음B", "industry_name": "반도체", "revenue": None},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200

    competitors = resp.json()["competitors"]
    names = [c["company_name"] for c in competitors]
    assert "매출있음A" in names
    assert "매출없음B" not in names


@pytest.mark.asyncio
async def test_vc_map_coefficient_serialization(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """coefficient 필드가 str로 직렬화된다."""
    await _seed_vc_coefficients(
        async_session,
        [
            {"source_industry": "반도체", "target_industry": "자동차", "coefficient": Decimal("0.123456")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200

    chain = resp.json()["forward_chains"][0]
    assert isinstance(chain["coefficient"], str)


@pytest.mark.asyncio
async def test_vc_map_revenue_serialization(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """revenue 필드가 str로 직렬화된다."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "직렬화기업", "industry_name": "반도체", "revenue": Decimal("1234.50")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체&min_revenue=0")
    assert resp.status_code == 200

    comp = resp.json()["competitors"][0]
    assert isinstance(comp["revenue"], str)


@pytest.mark.asyncio
async def test_vc_map_company_fields(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """VcChainCompany 응답에 모든 필드가 포함된다."""
    await _seed_vc_companies(
        async_session,
        [
            {
                "company_name": "필드확인사",
                "industry_name": "반도체",
                "io_sector_name": "전자부품",
                "corp_type": "유가증권시장",
                "revenue": Decimal("1000"),
                "listing_code": "005930",
            },
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체&min_revenue=0")
    assert resp.status_code == 200

    comp = resp.json()["competitors"][0]
    assert comp["company_name"] == "필드확인사"
    assert comp["industry_name"] == "반도체"
    assert comp["io_sector_name"] == "전자부품"
    assert comp["corp_type"] == "유가증권시장"
    assert comp["listing_code"] == "005930"
    assert comp["revenue"] is not None
    assert "id" in comp  # VcChainCompany에 id 필드 존재 검증


@pytest.mark.asyncio
async def test_vc_map_full_scenario(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """전방+후방+경쟁 모두 있는 통합 시나리오."""
    # 계수
    await _seed_vc_coefficients(
        async_session,
        [
            # 전방: 반도체 → 자동차, 가전
            {"source_industry": "반도체", "target_industry": "자동차", "coefficient": Decimal("0.100")},
            {"source_industry": "반도체", "target_industry": "가전", "coefficient": Decimal("0.080")},
            # 후방: 화학, 전력 → 반도체
            {"source_industry": "화학", "target_industry": "반도체", "coefficient": Decimal("0.120")},
            {"source_industry": "전력", "target_industry": "반도체", "coefficient": Decimal("0.060")},
        ],
    )
    # 기업
    await _seed_vc_companies(
        async_session,
        [
            # 경쟁사 (반도체)
            {"company_name": "삼성전자", "industry_name": "반도체", "revenue": Decimal("2000")},
            {"company_name": "SK하이닉스", "industry_name": "반도체", "revenue": Decimal("1500")},
            # 전방 업종 기업
            {"company_name": "현대차", "industry_name": "자동차", "revenue": Decimal("3000")},
            {"company_name": "LG전자", "industry_name": "가전", "revenue": Decimal("500")},
            # 후방 업종 기업
            {"company_name": "LG화학", "industry_name": "화학", "revenue": Decimal("800")},
            {"company_name": "한국전력", "industry_name": "전력", "revenue": Decimal("1200")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
    assert resp.status_code == 200
    data = resp.json()

    # 전체 구조 검증
    assert data["target_industry"] == "반도체"
    assert data["total_forward"] == 2
    assert data["total_backward"] == 2
    assert data["total_competitors"] == 2

    # 전방: 자동차(0.1) > 가전(0.08)
    assert data["forward_chains"][0]["industry_name"] == "자동차"
    assert data["forward_chains"][1]["industry_name"] == "가전"

    # 후방: 화학(0.12) > 전력(0.06)
    assert data["backward_chains"][0]["industry_name"] == "화학"
    assert data["backward_chains"][1]["industry_name"] == "전력"

    # 경쟁: 삼성전자(2000) > SK하이닉스(1500)
    assert data["competitors"][0]["company_name"] == "삼성전자"
    assert data["competitors"][1]["company_name"] == "SK하이닉스"

    # 전방 패널 내 기업
    auto_panel = data["forward_chains"][0]
    assert any(c["company_name"] == "현대차" for c in auto_panel["companies"])


@pytest.mark.asyncio
async def test_vc_map_only_competitors_no_coefficients(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """계수 없어도 동종 경쟁사만 반환 가능."""
    await _seed_vc_companies(
        async_session,
        [
            {"company_name": "경쟁사A", "industry_name": "바이오", "revenue": Decimal("200")},
        ],
    )

    resp = await client.get("/api/v1/si-mapping/vc-map?industry=바이오")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_forward"] == 0
    assert data["total_backward"] == 0
    assert data["total_competitors"] == 1
    assert data["competitors"][0]["company_name"] == "경쟁사A"


@pytest.mark.asyncio
async def test_vc_company_has_timestamps(
    async_session: AsyncSession,
) -> None:
    """VcCompany 모델이 TimestampMixin의 created_at/updated_at을 갖는다."""
    company = VcCompany(company_name="타임스탬프사", industry_name="반도체")
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    assert company.created_at is not None
    assert company.updated_at is not None


# ══════════════════════════════════════════════════════════
# Error Path Tests: 429 Rate Limit
# ══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_vc_map_429_rate_limit(client: AsyncClient) -> None:
    """VC 매핑 API rate limit 초과 시 429 응답."""
    from app.core.rate_limiter import si_rate_limiter

    original_max = si_rate_limiter._max_calls
    si_rate_limiter._max_calls = 0
    try:
        resp = await client.get("/api/v1/si-mapping/vc-map?industry=반도체")
        assert resp.status_code == 429
    finally:
        si_rate_limiter._max_calls = original_max


@pytest.mark.asyncio
async def test_vc_map_nonexistent_industry_empty_result(
    client: AsyncClient,
) -> None:
    """존재하지 않는 업종명 → forward/backward/competitive 모두 빈 리스트 (MAJ-13)."""
    resp = await client.get("/api/v1/si-mapping/vc-map?industry=절대존재않는업종XYZ123")
    assert resp.status_code == 200
    data = resp.json()

    assert data["target_industry"] == "절대존재않는업종XYZ123"
    assert data["forward_chains"] == []
    assert data["backward_chains"] == []
    assert data["competitors"] == []
    assert data["total_forward"] == 0
    assert data["total_backward"] == 0
    assert data["total_competitors"] == 0
