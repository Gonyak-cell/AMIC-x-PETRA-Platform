"""인허가 분석 API 테스트."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# ── KB Industries ──────────────────────────────────────────

async def test_list_industries(client: AsyncClient):
    """업종 목록 조회."""
    resp = await client.get("/api/v1/permits/kb/industries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 10  # 최소 10개 업종
    codes = [d["code"] for d in data]
    assert "FINANCE" in codes
    assert "TELECOM" in codes


# ── Analyze Permits ────────────────────────────────────────

async def test_analyze_permits_finance(client: AsyncClient, transaction_id: str):
    """금융업 인허가 분석 — KB 기반."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/analyze",
        json={
            "business_types": ["FINANCE_CREDIT"],
            "existing_permits": [],
        },
    )
    assert resp.status_code == 201
    analysis = resp.json()
    assert analysis["status"] == "COMPLETED"
    assert analysis["analysis_method"] == "KB_ONLY"
    assert "FINANCE_CREDIT" in analysis["business_types"]

    # 요건 확인
    resp2 = await client.get(f"/api/v1/transactions/{transaction_id}/permits/requirements")
    assert resp2.status_code == 200
    reqs = resp2.json()
    # 공통 (공정위) + 공통 (외투) + 여신전문 = 3개
    assert len(reqs) >= 2
    names = [r["permit_name"] for r in reqs]
    assert any("여신전문" in n for n in names)


async def test_analyze_permits_telecom(client: AsyncClient, transaction_id: str):
    """통신업 인허가 분석."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/analyze",
        json={
            "business_types": ["TELECOM_VALUE_ADDED"],
            "existing_permits": [],
        },
    )
    assert resp.status_code == 201

    resp2 = await client.get(f"/api/v1/transactions/{transaction_id}/permits/requirements")
    reqs = resp2.json()
    names = [r["permit_name"] for r in reqs]
    assert any("부가통신" in n for n in names)
    # 부가통신은 사후신고
    vat = next(r for r in reqs if "부가통신" in r["permit_name"])
    assert vat["timing_type"] == "POST_FILING"
    assert vat["post_filing_deadline_days"] == 14


async def test_analyze_permits_universal_threshold(client: AsyncClient):
    """공정위 기업결합신고 — 거래금액 미달 시 제외."""
    # deal_value가 없는 거래 (threshold 미달)
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "소규모 거래",
            "code_name": "SMALL-001",
            "side": "SELL",
            "target_company_name": "소규모 기업",
            "client_name": "고객",
            "lead_advisor_email": "test@example.com",
            "estimated_deal_value": 1_000_000_000,  # 10억 (300억 미달)
        },
    )
    assert resp.status_code == 201
    txn_id = resp.json()["id"]

    resp2 = await client.post(
        f"/api/v1/transactions/{txn_id}/permits/analyze",
        json={"business_types": ["CONSTRUCTION_GENERAL"], "existing_permits": []},
    )
    assert resp2.status_code == 201

    resp3 = await client.get(f"/api/v1/transactions/{txn_id}/permits/requirements")
    reqs = resp3.json()
    names = [r["permit_name"] for r in reqs]
    # 공정위 기업결합 신고는 제외되어야 함
    assert not any("기업결합" in n for n in names)
    # 건설업 변경신고는 포함
    assert any("건설업" in n for n in names)


# ── Get Analysis ───────────────────────────────────────────

async def test_get_analysis_none(client: AsyncClient, transaction_id: str):
    """분석 전 조회 → null."""
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/permits/analysis")
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_analysis_after_analyze(client: AsyncClient, transaction_id: str):
    """분석 후 조회."""
    await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/analyze",
        json={"business_types": ["FINANCE_BANK"], "existing_permits": []},
    )
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/permits/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"


# ── Reanalyze ──────────────────────────────────────────────

async def test_reanalyze_replaces_previous(client: AsyncClient, transaction_id: str):
    """재분석 시 기존 결과 교체."""
    await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/analyze",
        json={"business_types": ["FINANCE_CREDIT"], "existing_permits": []},
    )
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/analysis/reanalyze",
        json={"business_types": ["CONSTRUCTION_GENERAL"], "existing_permits": []},
    )
    assert resp.status_code == 201
    assert "CONSTRUCTION_GENERAL" in resp.json()["business_types"]

    reqs = (await client.get(f"/api/v1/transactions/{transaction_id}/permits/requirements")).json()
    names = [r["permit_name"] for r in reqs]
    assert any("건설업" in n for n in names)
    # 이전 여신전문 결과는 없어야 함
    assert not any("여신전문" in n for n in names)


# ── Manual CRUD ────────────────────────────────────────────

async def test_manual_requirement_crud(client: AsyncClient, transaction_id: str):
    """수동 인허가 요건 추가/수정/삭제."""
    # 먼저 분석 실행
    await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/analyze",
        json={"business_types": ["CONSTRUCTION_GENERAL"], "existing_permits": []},
    )
    # 수동 추가
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/requirements",
        json={
            "permit_name": "수동 추가 인허가",
            "regulatory_body": "테스트 기관",
            "filing_type": "CHANGE_NOTIFICATION",
            "timing_type": "POST_FILING",
            "post_filing_deadline_days": 7,
        },
    )
    assert resp.status_code == 201
    req = resp.json()
    assert req["source"] == "MANUAL"
    req_id = req["id"]

    # 수정
    resp2 = await client.patch(
        f"/api/v1/transactions/{transaction_id}/permits/requirements/{req_id}",
        json={"status": "FILED", "notes": "신고 완료"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "FILED"

    # 삭제
    resp3 = await client.delete(
        f"/api/v1/transactions/{transaction_id}/permits/requirements/{req_id}",
    )
    assert resp3.status_code == 204


async def test_create_requirement_without_analysis(client: AsyncClient, transaction_id: str):
    """분석 없이 수동 추가 시 400."""
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/permits/requirements",
        json={
            "permit_name": "테스트",
            "regulatory_body": "테스트",
            "filing_type": "CHANGE_NOTIFICATION",
            "timing_type": "POST_FILING",
        },
    )
    assert resp.status_code == 400


# ── KB lookup unit test ────────────────────────────────────

def test_kb_lookup_direct():
    """KB lookup 함수 직접 테스트."""
    from app.services.permit_knowledge_base import lookup_permits

    # 금융업(여신전문) + 지분인수 + 대형 거래
    results = lookup_permits(
        business_types=["FINANCE_CREDIT"],
        deal_structure="SHARE_ACQUISITION",
        deal_value=50_000_000_000,  # 500억
    )
    names = [r.permit_name for r in results]
    # 공정위 + 외투 + 여신전문 = 3개
    assert len(results) == 3
    assert any("기업결합" in n for n in names)
    assert any("여신전문" in n for n in names)


def test_kb_lookup_no_match():
    """매칭 안 되는 업종."""
    from app.services.permit_knowledge_base import lookup_permits

    results = lookup_permits(
        business_types=["NONEXISTENT_INDUSTRY"],
        deal_value=50_000_000_000,
    )
    # 공통 항목만 반환
    assert all(r.industry_code.startswith("UNIVERSAL_") for r in results)


def test_deadline_calculation():
    """기한 계산 테스트."""
    from app.services.permit_analysis_service import _calculate_deadline

    # 사전 30일
    assert _calculate_deadline("2026-04-01", "PRE_FILING", 30, None) == "2026-03-02"
    # 사후 14일
    assert _calculate_deadline("2026-04-01", "POST_FILING", None, 14) == "2026-04-15"
    # close_date 없으면 None
    assert _calculate_deadline(None, "PRE_FILING", 30, None) is None
