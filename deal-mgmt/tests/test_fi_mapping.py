"""FI 자동 매핑 (PEF 레지스트리 기반 GP 추천) 테스트.

알고리즘 검증:
  1. 2021-01-01 이후 결성 펀드만 대상
  2. 프로젝트 펀드 선택적 제외
  3. GP별 최소 펀드 약정총액 기준값 산출
  4. target * 0.5 ≤ min_fund_size ≤ target * 3 범위 매칭
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pef_fund_registry import PefFundRegistry

# ── 헬퍼 ─────────────────────────────────────────────────────


async def _create_txn(
    client: AsyncClient,
    deal_value: int | None,
    *,
    target_company_name: str = "테스트타깃",
) -> str:
    """deal_value(억원)를 지정하여 Transaction을 생성하고 ID를 반환한다."""
    payload: dict = {
        "name": "FI 매핑 테스트",
        "code_name": f"FI-TEST-{uuid.uuid4().hex[:8]}",
        "target_company_name": target_company_name,
        "client_name": "테스트고객",
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
            legal_basis=data.get("legal_basis"),
            registration_date=data.get("registration_date"),
            gp1=data.get("gp1"),
            gp2=data.get("gp2"),
            gp3=data.get("gp3"),
            total_committed_capital=data.get("total_committed_capital"),
        )
        async_session.add(pef)
    await async_session.commit()


def _fi_url(txn_id: str, **params: object) -> str:
    """FI 추천 API URL을 구성한다."""
    base = f"/api/v1/transactions/{txn_id}/fi-recommendations"
    if not params:
        return base
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{qs}"


# ── 기존 테스트 케이스 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_date_filter_excludes_old_funds(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """2021년 이전 펀드는 매핑에서 제외된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "올드펀드1호",
                "registration_date": "2019-06-15",
                "gp1": "올드캐피탈",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "올드펀드2호",
                "registration_date": "2020-12-31",
                "gp1": "올드캐피탈",
                "total_committed_capital": 800,
            },
            {
                "pef_name": "뉴펀드1호",
                "registration_date": "2022-03-01",
                "gp1": "뉴캐피탈",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    gp_names = [r["gp_name"] for r in recs]
    assert "뉴캐피탈" in gp_names
    assert "올드캐피탈" not in gp_names


@pytest.mark.asyncio
async def test_project_fund_exclusion_default(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """프로젝트 펀드는 기본적으로 제외된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "ABC프로젝트1호",
                "registration_date": "2022-01-01",
                "gp1": "프로젝트GP",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "일반블라인드1호",
                "registration_date": "2022-01-01",
                "gp1": "블라인드GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    gp_names = [r["gp_name"] for r in recs]
    assert "블라인드GP" in gp_names
    assert "프로젝트GP" not in gp_names


@pytest.mark.asyncio
async def test_project_fund_inclusion_when_disabled(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """exclude_project_funds=false 시 프로젝트 펀드도 포함된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "ABC프로젝트1호",
                "registration_date": "2022-01-01",
                "gp1": "프로젝트GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id, exclude_project_funds="false"))
    assert resp.status_code == 200
    recs = resp.json()

    gp_names = [r["gp_name"] for r in recs]
    assert "프로젝트GP" in gp_names


@pytest.mark.asyncio
async def test_min_fund_size_calculation(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """GP의 여러 펀드 중 최소값이 min_fund_size로 사용된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "A캐피탈 1호",
                "registration_date": "2022-01-01",
                "gp1": "A캐피탈",
                "total_committed_capital": 500,
            },
            {
                "pef_name": "A캐피탈 2호",
                "registration_date": "2022-06-01",
                "gp1": "A캐피탈",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "A캐피탈 3호",
                "registration_date": "2023-01-01",
                "gp1": "A캐피탈",
                "total_committed_capital": 3000,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    a_cap = next((r for r in recs if r["gp_name"] == "A캐피탈"), None)
    assert a_cap is not None
    assert a_cap["min_fund_size"] == 500.0
    assert a_cap["fund_count"] == 3


@pytest.mark.asyncio
async def test_range_filter_lower_bound(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """min_fund_size < target * 0.5 인 GP는 제외된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            # min_fund_size=400 → 1000*0.5=500 미만 → 제외
            {"pef_name": "소형1호", "registration_date": "2022-01-01", "gp1": "소형GP", "total_committed_capital": 400},
            # min_fund_size=600 → 500 이상 → 포함
            {"pef_name": "적정1호", "registration_date": "2022-01-01", "gp1": "적정GP", "total_committed_capital": 600},
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    gp_names = [r["gp_name"] for r in recs]
    assert "소형GP" not in gp_names
    assert "적정GP" in gp_names


@pytest.mark.asyncio
async def test_range_filter_upper_bound(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """min_fund_size > target * 3 인 GP는 제외된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            # min_fund_size=3500 → 1000*3=3000 초과 → 제외
            {
                "pef_name": "대형1호",
                "registration_date": "2022-01-01",
                "gp1": "대형GP",
                "total_committed_capital": 3500,
            },
            # min_fund_size=2500 → 3000 이하 → 포함
            {
                "pef_name": "중형1호",
                "registration_date": "2022-01-01",
                "gp1": "중형GP",
                "total_committed_capital": 2500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    gp_names = [r["gp_name"] for r in recs]
    assert "대형GP" not in gp_names
    assert "중형GP" in gp_names


@pytest.mark.asyncio
async def test_custom_multipliers(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """커스텀 배수 파라미터가 정상 적용된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            # min_fund_size=300 → 기본(0.5x=500) 미만이지만, 0.3x=300 이상 → 포함
            {
                "pef_name": "소형펀드",
                "registration_date": "2022-01-01",
                "gp1": "소형GP",
                "total_committed_capital": 300,
            },
            # min_fund_size=4000 → 기본(3x=3000) 초과이지만, 5x=5000 이하 → 포함
            {
                "pef_name": "대형펀드",
                "registration_date": "2022-01-01",
                "gp1": "대형GP",
                "total_committed_capital": 4000,
            },
        ],
    )

    resp = await client.get(
        _fi_url(txn_id, lower_multiplier="0.3", upper_multiplier="5.0"),
    )
    assert resp.status_code == 200
    recs = resp.json()

    gp_names = [r["gp_name"] for r in recs]
    assert "소형GP" in gp_names
    assert "대형GP" in gp_names


@pytest.mark.asyncio
async def test_sort_by_min_fund_size_desc(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """결과는 min_fund_size 내림차순으로 정렬된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {"pef_name": "B펀드", "registration_date": "2022-01-01", "gp1": "B_GP", "total_committed_capital": 800},
            {"pef_name": "A펀드", "registration_date": "2022-01-01", "gp1": "A_GP", "total_committed_capital": 2000},
            {"pef_name": "C펀드", "registration_date": "2022-01-01", "gp1": "C_GP", "total_committed_capital": 1200},
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    sizes = [r["min_fund_size"] for r in recs]
    assert sizes == sorted(sizes, reverse=True)
    assert recs[0]["gp_name"] == "A_GP"


@pytest.mark.asyncio
async def test_match_reason_format(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """match_reason이 한국어 포맷으로 생성된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "적합펀드",
                "registration_date": "2022-01-01",
                "gp1": "적합GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    reason = recs[0]["match_reason"]
    assert "최소 펀드" in reason
    assert "하한" in reason
    assert "상한" in reason
    assert "범위 내" in reason


@pytest.mark.asyncio
async def test_empty_when_no_post_2021_funds(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """2021년 이후 펀드가 없으면 빈 배열을 반환한다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "구형펀드1",
                "registration_date": "2018-01-01",
                "gp1": "구형GP",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "구형펀드2",
                "registration_date": "2020-12-31",
                "gp1": "구형GP",
                "total_committed_capital": 2000,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_gp_deduplication_across_slots(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """동일 GP가 gp1/gp2 양쪽에 등재되어도 펀드 중복이 없다."""
    txn_id = await _create_txn(client, 1000)
    shared_id = uuid.uuid4()
    await _seed_pefs(
        async_session,
        [
            {
                "id": shared_id,
                "pef_name": "공동펀드1호",
                "registration_date": "2022-01-01",
                "gp1": "듀얼GP",
                "gp2": "듀얼GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    dual = next((r for r in recs if r["gp_name"] == "듀얼GP"), None)
    assert dual is not None
    assert dual["fund_count"] == 1
    fund_ids = [f["id"] for f in dual["matching_funds"]]
    assert len(fund_ids) == len(set(fund_ids))


# ── TC-01: deal_value 경계값 테스트 ──────────────────────────


@pytest.mark.asyncio
async def test_empty_when_deal_value_is_none(
    client: AsyncClient,
) -> None:
    """estimated_deal_value가 None이면 빈 배열."""
    txn_id = await _create_txn(client, None)

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_empty_when_deal_value_is_zero(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """estimated_deal_value가 0이면 빈 배열."""
    txn_id = await _create_txn(client, 0)
    await _seed_pefs(
        async_session,
        [{"pef_name": "펀드A", "registration_date": "2022-01-01", "gp1": "GP_A", "total_committed_capital": 500}],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_empty_when_deal_value_is_negative(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """estimated_deal_value가 음수이면 빈 배열."""
    txn_id = await _create_txn(client, -100)
    await _seed_pefs(
        async_session,
        [{"pef_name": "펀드A", "registration_date": "2022-01-01", "gp1": "GP_A", "total_committed_capital": 500}],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    assert resp.json() == []


# ── TC-02: 배수 유효성 검증 ──────────────────────────────────


@pytest.mark.asyncio
async def test_422_invalid_upper_multiplier(
    client: AsyncClient,
) -> None:
    """upper_multiplier가 유효 범위 미만이면 422."""
    txn_id = await _create_txn(client, 1000)

    resp = await client.get(_fi_url(txn_id, upper_multiplier="0.5"))
    assert resp.status_code == 422


# ── TC-04: 타깃 기업명 기반 프로젝트 펀드 제외 ──────────────


@pytest.mark.asyncio
async def test_target_company_name_exclusion(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """타깃 기업명이 포함된 펀드는 제외된다."""
    txn_id = await _create_txn(client, 1000, target_company_name="ABC테크")
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "ABC테크인수1호",
                "registration_date": "2022-01-01",
                "gp1": "특수GP",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "일반블라인드1호",
                "registration_date": "2022-01-01",
                "gp1": "일반GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    gp_names = [r["gp_name"] for r in resp.json()]
    assert "특수GP" not in gp_names
    assert "일반GP" in gp_names


# ── TC-05: gp2/gp3 전용 GP ──────────────────────────────────


@pytest.mark.asyncio
async def test_gp_only_in_gp2_or_gp3(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """gp1이 아닌 gp2/gp3에만 등재된 GP도 매핑된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "GP2전용펀드",
                "registration_date": "2022-01-01",
                "gp2": "GP2전용캐피탈",
                "total_committed_capital": 1500,
            },
            {
                "pef_name": "GP3전용펀드",
                "registration_date": "2022-01-01",
                "gp3": "GP3전용캐피탈",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    gp_names = [r["gp_name"] for r in resp.json()]
    assert "GP2전용캐피탈" in gp_names
    assert "GP3전용캐피탈" in gp_names


# ── TC-06: limit 파라미터 ────────────────────────────────────


@pytest.mark.asyncio
async def test_limit_parameter(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """limit 파라미터로 결과 수를 제한한다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": f"GP{i}펀드",
                "registration_date": "2022-01-01",
                "gp1": f"GP{i}캐피탈",
                "total_committed_capital": 500 + i * 100,
            }
            for i in range(5)
        ],
    )

    resp = await client.get(_fi_url(txn_id, limit=2))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── TC-07: list_pef_funds / pef_fund_count 엔드포인트 ────────


@pytest.mark.asyncio
async def test_list_pef_funds(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """PEF 목록 조회 기본 동작."""
    await _seed_pefs(
        async_session,
        [
            {"pef_name": "리스트펀드1", "gp1": "리스트GP1", "total_committed_capital": 1000},
            {"pef_name": "리스트펀드2", "gp1": "리스트GP2", "total_committed_capital": 2000},
        ],
    )

    resp = await client.get("/api/v1/pef-registry")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_pef_funds_search(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """PEF 목록 GP명 검색 필터."""
    await _seed_pefs(
        async_session,
        [
            {"pef_name": "A펀드", "gp1": "알파캐피탈"},
            {"pef_name": "B펀드", "gp1": "베타캐피탈"},
        ],
    )

    resp = await client.get("/api/v1/pef-registry?search=알파")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["gp1"] == "알파캐피탈"


@pytest.mark.asyncio
async def test_pef_fund_count(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """PEF 총 건수 조회."""
    await _seed_pefs(
        async_session,
        [
            {"pef_name": "카운트1", "gp1": "카운트GP1"},
            {"pef_name": "카운트2", "gp1": "카운트GP2"},
        ],
    )

    resp = await client.get("/api/v1/pef-registry/count")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_pef_fund_count_with_search(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """PEF 건수 검색 필터 연동."""
    await _seed_pefs(
        async_session,
        [
            {"pef_name": "A펀드", "gp1": "알파캐피탈"},
            {"pef_name": "B펀드", "gp1": "베타캐피탈"},
        ],
    )

    resp = await client.get("/api/v1/pef-registry/count?search=알파")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── SCHEMA-01 직렬화 검증: Decimal → number (float) ──────────


@pytest.mark.asyncio
async def test_decimal_serialized_as_number(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Decimal 필드가 JSON에서 number(float)로 직렬화된다."""
    txn_id = await _create_txn(client, 1000)
    await _seed_pefs(
        async_session,
        [
            {
                "pef_name": "직렬화펀드",
                "registration_date": "2022-01-01",
                "gp1": "직렬화GP",
                "total_committed_capital": 1500,
            },
        ],
    )

    resp = await client.get(_fi_url(txn_id))
    assert resp.status_code == 200
    recs = resp.json()

    assert len(recs) == 1
    rec = recs[0]
    # JSON number (float/int), not string
    assert isinstance(rec["min_fund_size"], (int, float))
    assert isinstance(rec["total_committed_sum"], (int, float))
    # matching_funds 내부도 검증
    fund = rec["matching_funds"][0]
    assert isinstance(fund["total_committed_capital"], (int, float))
