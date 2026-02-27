"""SI(전략적 투자자) 자동 매핑 API + 서비스 테스트."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.io_transaction import IOTransaction
from app.models.ksic_io_mapping import KsicIoMapping
from app.models.si_company import SICompany

pytestmark = pytest.mark.anyio


# ── 헬퍼: 참조 데이터 시딩 ─────────────────────────────────
async def _seed_reference_data(session: AsyncSession) -> dict:
    """테스트용 KSIC 매핑 + IO 거래 + SI 기업 데이터 삽입."""
    # KSIC ↔ IO 매핑
    mappings = [
        KsicIoMapping(io_code="IO01", io_name="식료품", ksic_code="C10", ksic_name="식료품 제조업"),
        KsicIoMapping(io_code="IO01", io_name="식료품", ksic_code="C11", ksic_name="음료 제조업"),
        KsicIoMapping(io_code="IO02", io_name="섬유", ksic_code="C13", ksic_name="섬유제품 제조업"),
        KsicIoMapping(io_code="IO03", io_name="화학제품", ksic_code="C20", ksic_name="화학물질 제조업"),
        KsicIoMapping(io_code="IO04", io_name="전자부품", ksic_code="C26", ksic_name="전자부품 제조업"),
    ]
    session.add_all(mappings)

    # IO 거래: IO01(식료품)의 공급자=IO03(화학), 수요자=IO02(섬유)
    transactions = [
        IOTransaction(source_io_code="IO03", source_io_name="화학제품", target_io_code="IO01", target_io_name="식료품", transaction_value=5000.0),
        IOTransaction(source_io_code="IO04", source_io_name="전자부품", target_io_code="IO01", target_io_name="식료품", transaction_value=3000.0),
        IOTransaction(source_io_code="IO01", source_io_name="식료품", target_io_code="IO02", target_io_name="섬유", transaction_value=4000.0),
        IOTransaction(source_io_code="IO01", source_io_name="식료품", target_io_code="IO04", target_io_name="전자부품", transaction_value=2000.0),
    ]
    session.add_all(transactions)

    # SI 기업
    companies = {
        "direct": SICompany(id=uuid.uuid4(), company_name="동종기업A", ksic_codes=["C10"], revenue=15_000_000_000, has_investment_history=True),
        "direct_low_rev": SICompany(id=uuid.uuid4(), company_name="동종기업B_저매출", ksic_codes=["C10"], revenue=5_000_000_000, has_investment_history=False),
        "backward": SICompany(id=uuid.uuid4(), company_name="공급자기업A", ksic_codes=["C20"], revenue=20_000_000_000, has_investment_history=False),
        "forward": SICompany(id=uuid.uuid4(), company_name="수요자기업A", ksic_codes=["C13"], revenue=12_000_000_000, has_investment_history=True),
        "unrelated": SICompany(id=uuid.uuid4(), company_name="무관기업", ksic_codes=["C99"], revenue=30_000_000_000, has_investment_history=False),
    }
    session.add_all(companies.values())
    await session.commit()
    return {k: str(v.id) for k, v in companies.items()}


# ── Stats ──────────────────────────────────────────────────


async def test_stats_empty(client: AsyncClient):
    """시딩 전 stats는 모두 0, is_seeded=false."""
    resp = await client.get("/api/v1/si-mapping/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["si_companies_count"] == 0
    assert body["ksic_io_mappings_count"] == 0
    assert body["io_transactions_count"] == 0
    assert body["is_seeded"] is False


async def test_stats_after_seed(client: AsyncClient, async_session: AsyncSession):
    """시딩 후 건수 반환, is_seeded=true."""
    await _seed_reference_data(async_session)
    resp = await client.get("/api/v1/si-mapping/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["si_companies_count"] == 5
    assert body["ksic_io_mappings_count"] == 5
    assert body["io_transactions_count"] == 4
    assert body["is_seeded"] is True


# ── KSIC Search ────────────────────────────────────────────


async def test_ksic_search(client: AsyncClient, async_session: AsyncSession):
    """KSIC 코드 자동완성 검색 — 'C10' 매칭."""
    await _seed_reference_data(async_session)
    resp = await client.get("/api/v1/si-mapping/ksic/search?q=C10")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert any(item["code"] == "C10" for item in body)


async def test_ksic_search_by_name(client: AsyncClient, async_session: AsyncSession):
    """KSIC 이름으로 검색 — '화학' 매칭."""
    await _seed_reference_data(async_session)
    resp = await client.get("/api/v1/si-mapping/ksic/search?q=화학")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert any(item["code"] == "C20" for item in body)


async def test_ksic_search_empty(client: AsyncClient, async_session: AsyncSession):
    """빈 쿼리 → 빈 결과."""
    await _seed_reference_data(async_session)
    resp = await client.get("/api/v1/si-mapping/ksic/search?q=")
    assert resp.status_code == 200
    assert resp.json() == []


# ── SI Mapping ─────────────────────────────────────────────


async def test_map_direct_peers(client: AsyncClient, async_session: AsyncSession):
    """KSIC C10 → 동종업계 기업 반환 (기본: 매출 필터 없음)."""
    await _seed_reference_data(async_session)
    resp = await client.post("/api/v1/si-mapping/map", json={"ksic_codes": ["C10"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_ksic_codes"] == ["C10"]
    # min_revenue=null(기본) → 매출 무관 전체 동종업계 반환
    peer_names = [p["company_name"] for p in body["direct_peers"]]
    assert "동종기업A" in peer_names
    assert "동종기업B_저매출" in peer_names


async def test_map_direct_peers_with_revenue_filter(client: AsyncClient, async_session: AsyncSession):
    """KSIC C10 + min_revenue=100억 → 고매출 기업만 반환."""
    await _seed_reference_data(async_session)
    resp = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "min_revenue": 10_000_000_000},
    )
    assert resp.status_code == 200
    body = resp.json()
    peer_names = [p["company_name"] for p in body["direct_peers"]]
    assert "동종기업A" in peer_names
    assert "동종기업B_저매출" not in peer_names


async def test_map_backward_chain(client: AsyncClient, async_session: AsyncSession):
    """IO01(식료품) 공급자 체인 — IO03(화학)에 속한 기업 반환."""
    await _seed_reference_data(async_session)
    resp = await client.post("/api/v1/si-mapping/map", json={"ksic_codes": ["C10"]})
    assert resp.status_code == 200
    body = resp.json()
    backward = body["backward_chain"]
    assert len(backward) > 0
    # IO03(화학)이 가장 높은 거래액 (5000)
    assert backward[0]["io_code"] == "IO03"
    # 공급자기업A가 포함
    company_names = [c["company_name"] for c in backward[0]["companies"]]
    assert "공급자기업A" in company_names


async def test_map_forward_chain(client: AsyncClient, async_session: AsyncSession):
    """IO01(식료품) 수요자 체인 — IO02(섬유)에 속한 기업 반환."""
    await _seed_reference_data(async_session)
    resp = await client.post("/api/v1/si-mapping/map", json={"ksic_codes": ["C10"]})
    assert resp.status_code == 200
    body = resp.json()
    forward = body["forward_chain"]
    assert len(forward) > 0
    # IO02(섬유)가 가장 높은 거래액 (4000)
    assert forward[0]["io_code"] == "IO02"
    company_names = [c["company_name"] for c in forward[0]["companies"]]
    assert "수요자기업A" in company_names


async def test_map_with_no_min_revenue(client: AsyncClient, async_session: AsyncSession):
    """min_revenue=null → 저매출 기업도 포함."""
    await _seed_reference_data(async_session)
    resp = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "min_revenue": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    peer_names = [p["company_name"] for p in body["direct_peers"]]
    assert "동종기업B_저매출" in peer_names


async def test_map_with_investment_filter(client: AsyncClient, async_session: AsyncSession):
    """require_investment_history=true → 투자이력 있는 기업만."""
    await _seed_reference_data(async_session)
    resp = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "min_revenue": None, "require_investment_history": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    peer_names = [p["company_name"] for p in body["direct_peers"]]
    assert "동종기업A" in peer_names
    assert "동종기업B_저매출" not in peer_names


async def test_map_all_candidates_dedup(client: AsyncClient, async_session: AsyncSession):
    """all_candidates에서 중복 기업 제거 확인."""
    await _seed_reference_data(async_session)
    resp = await client.post(
        "/api/v1/si-mapping/map",
        json={"ksic_codes": ["C10"], "min_revenue": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    company_ids = [c["company"]["id"] for c in body["all_candidates"]]
    assert len(company_ids) == len(set(company_ids))


# ── Bulk Add Buyers ────────────────────────────────────────


async def test_bulk_add_buyers(client: AsyncClient, async_session: AsyncSession, transaction_id: str):
    """SI → BuyerCandidate 등록 성공."""
    ids = await _seed_reference_data(async_session)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/si-mapping/add-buyers",
        json={"si_company_ids": [ids["direct"], ids["backward"]]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["added_count"] == 2
    assert body["skipped_count"] == 0
    assert len(body["buyer_ids"]) == 2


async def test_bulk_add_skip_duplicates(client: AsyncClient, async_session: AsyncSession, transaction_id: str):
    """동일 기업 중복 등록 시 skip."""
    ids = await _seed_reference_data(async_session)
    # 첫 번째 등록
    await client.post(
        f"/api/v1/transactions/{transaction_id}/si-mapping/add-buyers",
        json={"si_company_ids": [ids["direct"]]},
    )
    # 두 번째 등록 (중복 포함)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/si-mapping/add-buyers",
        json={"si_company_ids": [ids["direct"], ids["backward"]]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["added_count"] == 1  # backward만 추가
    assert body["skipped_count"] == 1  # direct은 skip
