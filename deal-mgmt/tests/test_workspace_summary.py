"""워크스페이스 요약 (배지 카운트) API 테스트."""

import uuid

BASIC_TXN = {
    "name": "워크스페이스 요약 테스트",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=BASIC_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


# ── 기본 동작 ──────────────────────────────────────────────


async def test_workspace_summary_initial(client):
    """새 거래의 workspace-summary — 시드 데이터(closing 등) 제외 0."""
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/workspace-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["buyer_count"] == 0
    assert data["engagement_count"] == 0
    assert data["timeline_count"] == 0
    assert data["nda_count"] == 0
    assert data["bid_count"] == 0
    assert data["dd_item_count"] == 0
    assert data["contract_count"] == 0
    # closing_item_count: deal_setup이 표준 체크리스트를 자동 생성하므로 >= 0
    assert isinstance(data["closing_item_count"], int)
    assert data["closing_item_count"] >= 0
    assert data["pmi_count"] == 0
    assert data["earnout_count"] == 0
    assert data["marketing_material_count"] == 0
    assert data["financial_model_count"] == 0
    assert data["legal_document_count"] == 0


async def test_workspace_summary_has_all_fields(client):
    """응답에 13개 카운트 필드가 모두 존재."""
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/workspace-summary")
    data = resp.json()
    expected_fields = {
        "buyer_count",
        "engagement_count",
        "timeline_count",
        "nda_count",
        "bid_count",
        "dd_item_count",
        "contract_count",
        "closing_item_count",
        "pmi_count",
        "earnout_count",
        "marketing_material_count",
        "financial_model_count",
        "legal_document_count",
    }
    assert expected_fields == set(data.keys())


# ── 카운트 정확성 ─────────────────────────────────────────


async def test_workspace_summary_counts_buyers(client):
    """매수자 추가 후 buyer_count 반영 확인."""
    txn_id = await _create_txn(client)

    # 매수자 2명 추가
    for i in range(2):
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/buyers",
            json={
                "company_name": f"매수자{i}",
                "buyer_type": "STRATEGIC",
                "tier": "TIER_1",
            },
        )
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workspace-summary")
    assert resp.json()["buyer_count"] == 2


async def test_workspace_summary_counts_engagements(client):
    """수임 추가 후 engagement_count 반영 확인."""
    txn_id = await _create_txn(client)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json={"type": "EXCLUSIVE"},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workspace-summary")
    assert resp.json()["engagement_count"] == 1


async def test_workspace_summary_counts_ndas(client):
    """NDA 추가 후 nda_count 반영 확인."""
    txn_id = await _create_txn(client)

    # NDA 생성에 buyer_candidate_id 필수 → 먼저 매수자 생성
    buyer_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={
            "company_name": "NDA대상",
            "buyer_type": "STRATEGIC",
            "tier": "TIER_1",
        },
    )
    assert buyer_resp.status_code == 201
    buyer_id = buyer_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={
            "buyer_candidate_id": buyer_id,
            "nda_type": "MUTUAL",
        },
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workspace-summary")
    assert resp.json()["nda_count"] == 1


# ── 격리 검증 ─────────────────────────────────────────────


async def test_workspace_summary_isolation(client):
    """다른 거래의 데이터가 카운트에 포함되지 않음."""
    txn_a = await _create_txn(client)
    txn_b = await _create_txn(client)

    # txn_a에만 매수자 추가
    await client.post(
        f"/api/v1/transactions/{txn_a}/buyers",
        json={
            "company_name": "A전용매수자",
            "buyer_type": "FINANCIAL",
            "tier": "TIER_2",
        },
    )

    # txn_b의 buyer_count는 0이어야 함
    resp = await client.get(f"/api/v1/transactions/{txn_b}/workspace-summary")
    assert resp.json()["buyer_count"] == 0


# ── 에러 케이스 ───────────────────────────────────────────


async def test_workspace_summary_not_found(client):
    """존재하지 않는 거래 ID → 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{fake_id}/workspace-summary")
    assert resp.status_code == 404
