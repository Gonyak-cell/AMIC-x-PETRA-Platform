"""Document Extraction HTTP API 테스트 — 엔드포인트 수준 검증."""

import uuid


async def _create_txn(client) -> str:
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "name": "추출 테스트 거래",
            "deal_type": "MA",
            "side": "SELL",
            "target_company_name": "기업",
            "client_name": "고객",
            "lead_advisor_email": "advisor@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── List extractions ─────────────────────────────────────
async def test_list_extractions_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/extractions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ── Get extraction — 존재하지 않는 추출 ──────────────────
async def test_get_extraction_nonexistent(client):
    txn_id = await _create_txn(client)
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{txn_id}/extractions/{fake_id}")
    assert resp.status_code == 404


# ── 잘못된 거래 ID ───────────────────────────────────────
async def test_extraction_invalid_txn(client):
    fake_txn = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{fake_txn}/extractions")
    assert resp.status_code == 404


# ── Batch extraction — 빈 리스트 ─────────────────────────
async def test_batch_extraction_empty_list(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/extractions/batch",
        json={"vdr_document_ids": []},
    )
    # 빈 리스트는 400 또는 422
    assert resp.status_code in (400, 422)
