"""SI(전략적 투자자) 자동 매핑 API + 서비스 테스트.

SI 매핑(KSIC 기반)과 VC 매핑(업종 계수 기반)을 모두 커버합니다.
파일이 커지면 test_si_mapping.py / test_vc_mapping.py로 분리를 고려하세요.
"""

import json
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.io_sector import IOSector
from app.models.io_transaction import IOTransaction
from app.models.ksic_io_mapping import KsicIoMapping
from app.models.si_company import SICompany
from app.services.si_mapping_service import (
    _build_ksic_index,
    _lookup_by_ksic,
)

pytestmark = pytest.mark.anyio


# ── 헬퍼: 참조 데이터 시딩 ─────────────────────────────────
async def _seed_reference_data(session: AsyncSession) -> dict:
    """테스트용 IO 부문 + KSIC 매핑 + IO 거래 + SI 기업 데이터 삽입."""
    # IO 부문분류 마스터 (FK 참조 대상, 가장 먼저 삽입)
    sectors = [
        IOSector(code="IO01", name="식료품"),
        IOSector(code="IO02", name="섬유"),
        IOSector(code="IO03", name="화학제품"),
        IOSector(code="IO04", name="전자부품"),
    ]
    session.add_all(sectors)
    await session.flush()

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
        IOTransaction(
            source_io_code="IO03",
            source_io_name="화학제품",
            target_io_code="IO01",
            target_io_name="식료품",
            transaction_value=5000.0,
        ),
        IOTransaction(
            source_io_code="IO04",
            source_io_name="전자부품",
            target_io_code="IO01",
            target_io_name="식료품",
            transaction_value=3000.0,
        ),
        IOTransaction(
            source_io_code="IO01",
            source_io_name="식료품",
            target_io_code="IO02",
            target_io_name="섬유",
            transaction_value=4000.0,
        ),
        IOTransaction(
            source_io_code="IO01",
            source_io_name="식료품",
            target_io_code="IO04",
            target_io_name="전자부품",
            transaction_value=2000.0,
        ),
    ]
    session.add_all(transactions)

    # SI 기업
    companies = {
        "direct": SICompany(
            id=uuid.uuid4(),
            company_name="동종기업A",
            ksic_codes=["C10"],
            revenue=15_000_000_000,
            has_investment_history=True,
        ),
        "direct_low_rev": SICompany(
            id=uuid.uuid4(),
            company_name="동종기업B_저매출",
            ksic_codes=["C10"],
            revenue=5_000_000_000,
            has_investment_history=False,
        ),
        "backward": SICompany(
            id=uuid.uuid4(),
            company_name="공급자기업A",
            ksic_codes=["C20"],
            revenue=20_000_000_000,
            has_investment_history=False,
        ),
        "forward": SICompany(
            id=uuid.uuid4(),
            company_name="수요자기업A",
            ksic_codes=["C13"],
            revenue=12_000_000_000,
            has_investment_history=True,
        ),
        "unrelated": SICompany(
            id=uuid.uuid4(),
            company_name="무관기업",
            ksic_codes=["C99"],
            revenue=30_000_000_000,
            has_investment_history=False,
        ),
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


async def test_map_unknown_ksic_codes(client: AsyncClient, async_session: AsyncSession):
    """존재하지 않는 KSIC 코드 → 빈 결과 반환."""
    await _seed_reference_data(async_session)
    resp = await client.post("/api/v1/si-mapping/map", json={"ksic_codes": ["Z99"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["direct_peers"] == []
    assert body["backward_chain"] == []
    assert body["forward_chain"] == []
    assert body["all_candidates"] == []


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


# ── Error Path Tests ──────────────────────────────────────


async def test_map_empty_ksic_codes(client: AsyncClient, async_session: AsyncSession):
    """빈 ksic_codes 목록 → 422 검증 에러."""
    await _seed_reference_data(async_session)
    resp = await client.post("/api/v1/si-mapping/map", json={"ksic_codes": []})
    assert resp.status_code == 422


async def test_ksic_search_special_chars(client: AsyncClient, async_session: AsyncSession):
    """LIKE 와일드카드 특수문자(%_) 검색 → 에러 없이 빈 결과."""
    await _seed_reference_data(async_session)
    resp = await client.get("/api/v1/si-mapping/ksic/search?q=%25test_")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_bulk_add_nonexistent_company(client: AsyncClient, async_session: AsyncSession, transaction_id: str):
    """존재하지 않는 SI 기업 ID → 에러 없이 스킵."""
    await _seed_reference_data(async_session)
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/si-mapping/add-buyers",
        json={"si_company_ids": [fake_id]},
    )
    # 존재하지 않는 ID는 스킵되어 added=0
    assert resp.status_code == 201
    body = resp.json()
    assert body["added_count"] == 0
    assert body["skipped_count"] == 0


# ── 접두사 매칭 + 이중 직렬화 방어 테스트 ─────────────────


async def test_prefix_matching_short_to_long(async_session: AsyncSession):
    """역접두사 매칭 — 기업 KSIC 'C10'이 조회 코드 'C1011'과 매칭 (최소 3글자)."""
    company = SICompany(
        id=uuid.uuid4(),
        company_name="접두사기업",
        ksic_codes=["C10"],
        revenue=10_000_000_000,
    )
    index, sorted_keys = _build_ksic_index([company])
    # "C1011"으로 조회 → 인덱스 키 "C10"이 "C1011"의 접두사(3글자↑)이므로 매칭
    result = _lookup_by_ksic(index, sorted_keys, ["C1011"])
    assert len(result) == 1
    assert result[0].company_name == "접두사기업"


async def test_prefix_matching_long_to_short(async_session: AsyncSession):
    """역접두사 매칭 — 기업 KSIC 'C101'이 조회 코드 'C10'과 매칭."""
    company = SICompany(
        id=uuid.uuid4(),
        company_name="세부업종기업",
        ksic_codes=["C101"],
        revenue=10_000_000_000,
    )
    index, sorted_keys = _build_ksic_index([company])
    # "C10"으로 조회 → 인덱스 키 "C101"이 "C10"으로 시작하므로 매칭
    result = _lookup_by_ksic(index, sorted_keys, ["C10"])
    assert len(result) == 1
    assert result[0].company_name == "세부업종기업"


async def test_prefix_matching_exact_still_works(async_session: AsyncSession):
    """정확 매칭 + 접두사 매칭이 모두 동작."""
    exact = SICompany(
        id=uuid.uuid4(),
        company_name="정확매칭기업",
        ksic_codes=["C101"],
        revenue=10_000_000_000,
    )
    prefix = SICompany(
        id=uuid.uuid4(),
        company_name="접두사매칭기업",
        ksic_codes=["C10"],
        revenue=5_000_000_000,
    )
    index, sorted_keys = _build_ksic_index([exact, prefix])
    # "C101" 정확 매칭 + "C10"이 역접두사 매칭
    result = _lookup_by_ksic(index, sorted_keys, ["C101"])
    names = [c.company_name for c in result]
    assert "정확매칭기업" in names
    assert "접두사매칭기업" in names


async def test_prefix_matching_no_false_positive(async_session: AsyncSession):
    """관련 없는 코드는 매칭하지 않음."""
    company = SICompany(
        id=uuid.uuid4(),
        company_name="무관기업",
        ksic_codes=["C99"],
        revenue=10_000_000_000,
    )
    index, sorted_keys = _build_ksic_index([company])
    result = _lookup_by_ksic(index, sorted_keys, ["C10"])
    assert len(result) == 0


async def test_build_ksic_index_handles_double_serialized():
    """_build_ksic_index가 이중 직렬화된 ksic_codes(str)를 복원 처리."""
    company = SICompany(
        id=uuid.uuid4(),
        company_name="이중직렬화기업",
    )
    # 이중 직렬화 시뮬레이션: ORM을 거치지 않고 직접 str 설정
    object.__setattr__(company, "ksic_codes", json.dumps(["C10", "C20"]))

    index, _sorted_keys = _build_ksic_index([company])
    assert "C10" in index
    assert "C20" in index
    assert len(index["C10"]) == 1
    assert index["C10"][0].company_name == "이중직렬화기업"


async def test_build_ksic_index_handles_normal_list():
    """_build_ksic_index가 정상 list 타입 ksic_codes를 올바르게 처리."""
    company = SICompany(
        id=uuid.uuid4(),
        company_name="정상기업",
        ksic_codes=["C10", "C20"],
        revenue=10_000_000_000,
    )
    index, _sorted_keys = _build_ksic_index([company])
    assert "C10" in index
    assert "C20" in index


async def test_map_prefix_matching_via_api(client: AsyncClient, async_session: AsyncSession):
    """API 레벨 역접두사 매칭 — '101' KSIC 보유 기업이 '1011' 쿼리에 포함 (3글자↑).

    주의: API는 _strip_ksic_prefix()로 쿼리 코드의 알파벳 접두사를 제거하지만,
    인덱스 키(회사 KSIC)는 strip하지 않으므로 숫자 전용 코드를 사용해야 대칭이 맞다.
    """
    # IO 부문 + 매핑 시딩
    sectors = [IOSector(code="IO01", name="식료품")]
    session = async_session
    session.add_all(sectors)
    await session.flush()

    mappings = [
        KsicIoMapping(io_code="IO01", io_name="식료품", ksic_code="1011", ksic_name="식료품"),
    ]
    session.add_all(mappings)

    # KSIC "101" 보유 기업 (역접두사 매칭 대상 — 101은 1011의 접두사, 3글자↑)
    company = SICompany(
        id=uuid.uuid4(),
        company_name="접두사매칭API기업",
        ksic_codes=["101"],
        revenue=10_000_000_000,
    )
    session.add(company)
    await session.commit()

    resp = await client.post("/api/v1/si-mapping/map", json={"ksic_codes": ["1011"]})
    assert resp.status_code == 200
    body = resp.json()
    peer_names = [p["company_name"] for p in body["direct_peers"]]
    assert "접두사매칭API기업" in peer_names


# ══════════════════════════════════════════════════════════
# 등록번호 기반 VC 매핑 테스트
# ══════════════════════════════════════════════════════════


async def _seed_vc_company(session: AsyncSession) -> int:
    """테스트용 VcCompany 1건 시드."""
    from app.models.vc_company import VcCompany

    vc = VcCompany(
        company_name="테스트전자",
        industry_name="반도체 제조업",
        corp_reg_no="110111-1234567",
        biz_reg_no="101-81-12345",
        revenue=Decimal("5000.00"),
    )
    session.add(vc)
    await session.flush()
    return vc.id


async def _seed_vc_companies(session: AsyncSession) -> list[int]:
    """테스트용 VcCompany 3건 시드 (bulk_add 테스트용)."""
    from app.models.vc_company import VcCompany

    companies = [
        VcCompany(
            company_name="VC기업A",
            industry_name="반도체 제조업",
            revenue=Decimal("1000.00"),
        ),
        VcCompany(
            company_name="VC기업B",
            industry_name="화학 제조업",
            revenue=Decimal("2000.00"),
        ),
        VcCompany(
            company_name="VC기업C",
            industry_name="전자부품 제조업",
            revenue=Decimal("3000.00"),
        ),
    ]
    session.add_all(companies)
    await session.flush()
    return [c.id for c in companies]


async def test_normalize_reg_no_strips_hyphens_spaces() -> None:
    """_normalize_reg_no가 하이픈과 공백을 모두 제거."""
    from app.services.si_mapping_service import _normalize_reg_no

    assert _normalize_reg_no("110111-1234567") == "1101111234567"
    assert _normalize_reg_no("101-81-12345") == "1018112345"
    assert _normalize_reg_no("110111 1234567") == "1101111234567"
    assert _normalize_reg_no("110111- 1234567") == "1101111234567"
    assert _normalize_reg_no("1234567890") == "1234567890"


async def test_find_vc_company_by_corp_reg_no(async_session: AsyncSession) -> None:
    """법인등록번호로 VcCompany를 정확히 조회."""
    from app.services.si_mapping_service import find_vc_company_by_registration

    await _seed_vc_company(async_session)
    await async_session.commit()

    # 하이픈 포함 검색
    result = await find_vc_company_by_registration(async_session, corp_reg_no="110111-1234567")
    assert result is not None
    assert result.company_name == "테스트전자"
    assert result.industry_name == "반도체 제조업"
    assert result.revenue == Decimal("5000.00")

    # 하이픈 없이 검색
    result = await find_vc_company_by_registration(async_session, corp_reg_no="1101111234567")
    assert result is not None
    assert result.company_name == "테스트전자"


async def test_find_vc_company_by_biz_reg_no(async_session: AsyncSession) -> None:
    """사업자등록번호 fallback 조회."""
    from app.services.si_mapping_service import find_vc_company_by_registration

    await _seed_vc_company(async_session)
    await async_session.commit()

    result = await find_vc_company_by_registration(async_session, biz_reg_no="101-81-12345")
    assert result is not None
    assert result.company_name == "테스트전자"


async def test_find_vc_company_not_found(async_session: AsyncSession) -> None:
    """등록번호가 없으면 None 반환."""
    from app.services.si_mapping_service import find_vc_company_by_registration

    result = await find_vc_company_by_registration(async_session, corp_reg_no="999999-9999999")
    assert result is None


async def test_find_vc_company_by_both_reg_nos(async_session: AsyncSession) -> None:
    """corp_reg_no + biz_reg_no 동시 제공 시 OR 쿼리."""
    from app.services.si_mapping_service import find_vc_company_by_registration

    await _seed_vc_company(async_session)
    await async_session.commit()

    result = await find_vc_company_by_registration(
        async_session,
        corp_reg_no="110111-1234567",
        biz_reg_no="101-81-12345",
    )
    assert result is not None
    assert result.company_name == "테스트전자"


async def test_normalize_reg_no_edge_cases() -> None:
    """_normalize_reg_no 경계값 테스트."""
    from app.services.si_mapping_service import _normalize_reg_no

    assert _normalize_reg_no("") == ""
    assert _normalize_reg_no("   ") == ""
    assert _normalize_reg_no("---") == ""
    assert _normalize_reg_no("- - -") == ""


# ── VC → BuyerCandidate 일괄 등록 ─────────────────────────


async def test_bulk_add_vc_buyers(
    client: AsyncClient,
    async_session: AsyncSession,
    transaction_id: str,
) -> None:
    """VC 기업 → BuyerCandidate 정상 등록."""
    vc_ids = await _seed_vc_companies(async_session)
    await async_session.commit()
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/vc-mapping/add-buyers",
        json={"vc_company_ids": [vc_ids[0], vc_ids[1]]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["added_count"] == 2
    assert body["skipped_count"] == 0
    assert len(body["buyer_ids"]) == 2


async def test_bulk_add_vc_buyers_skip_duplicates(
    client: AsyncClient,
    async_session: AsyncSession,
    transaction_id: str,
) -> None:
    """VC 기업 중복 등록 시 skip."""
    vc_ids = await _seed_vc_companies(async_session)
    await async_session.commit()
    # 첫 번째 등록
    await client.post(
        f"/api/v1/transactions/{transaction_id}/vc-mapping/add-buyers",
        json={"vc_company_ids": [vc_ids[0]]},
    )
    # 두 번째 등록 (중복 + 신규)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/vc-mapping/add-buyers",
        json={"vc_company_ids": [vc_ids[0], vc_ids[1]]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["added_count"] == 1  # vc_ids[1]만 추가
    assert body["skipped_count"] == 1  # vc_ids[0]은 skip


async def test_bulk_add_vc_buyers_not_found(
    client: AsyncClient,
    async_session: AsyncSession,
    transaction_id: str,
) -> None:
    """존재하지 않는 VC 기업 ID → not_found."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/vc-mapping/add-buyers",
        json={"vc_company_ids": [999999]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["added_count"] == 0
    assert body["not_found_count"] == 1
