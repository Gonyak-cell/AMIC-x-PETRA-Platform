"""Buyer 상태 전이 검증 테스트 — 유효/무효 전이 확인.

BuyerCandidateStatus: IDENTIFIED → CONTACTED → NDA_SENT → NDA_SIGNED → ...
"""

import uuid

SAMPLE_TXN = {
    "name": "전이 테스트 거래",
    "deal_type": "MA",
    "side": "SELL",
    "target_company_name": "기업",
    "client_name": "고객",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_BUYER = {
    "company_name": "매수후보",
    "buyer_type": "STRATEGIC",
    "contact_name": "김후보",
    "contact_email": "buyer@corp.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_buyer(client, txn_id: str) -> dict:
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=SAMPLE_BUYER)
    assert resp.status_code == 201
    return resp.json()


# ── 초기 상태 확인 ────────────────────────────────────────
async def test_new_buyer_is_identified(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    assert buyer["status"] == "IDENTIFIED"


# ── 유효 전이 ────────────────────────────────────────────
async def test_identified_to_contacted(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "CONTACTED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONTACTED"


async def test_contacted_to_nda_sent(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    # IDENTIFIED → CONTACTED
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "CONTACTED"},
    )
    # CONTACTED → NDA_SENT
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "NDA_SENT"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "NDA_SENT"


# ── 무효 전이 ────────────────────────────────────────────
async def test_skip_contacted_from_identified(client):
    """IDENTIFIED → NDA_SENT 직접 전이 불가 (CONTACTED 건너뜀)."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "NDA_SENT"},
    )
    assert resp.status_code in (400, 422)


async def test_backward_transition_rejected(client):
    """CONTACTED → IDENTIFIED 역방향 전이 불가."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "CONTACTED"},
    )
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "IDENTIFIED"},
    )
    assert resp.status_code in (400, 422)


async def test_reject_buyer(client):
    """IDENTIFIED → REJECTED 전이 가능."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "REJECTED", "rejection_reason": "전략적 적합성 부족"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


# ── 에러 케이스 ──────────────────────────────────────────
async def test_nonexistent_buyer_transition(client):
    txn_id = await _create_txn(client)
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{fake_id}",
        json={"status": "CONTACTED"},
    )
    assert resp.status_code == 404


async def test_invalid_status_value(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "NOT_A_STATUS"},
    )
    assert resp.status_code == 422
