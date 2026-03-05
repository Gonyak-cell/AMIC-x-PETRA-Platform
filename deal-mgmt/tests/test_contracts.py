"""계약/SPA 관리 API 테스트."""

SAMPLE_TXN = {
    "name": "계약 테스트 거래",
    "deal_type": "MA",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    return resp.json()["id"]


# ── Create ─────────────────────────────────────────────────
async def test_create_contract(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "주식매매계약(SPA)", "contract_type": "SPA"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "주식매매계약(SPA)"
    assert data["contract_type"] == "SPA"
    assert data["status"] == "DRAFT"
    assert data["seller_signature"] == "PENDING"
    assert data["buyer_signature"] == "PENDING"
    assert data["current_version"] == 1


async def test_create_contract_minimal(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "사이드레터"},
    )
    assert resp.status_code == 201
    assert resp.json()["contract_type"] == "SPA"  # server default


# ── List ───────────────────────────────────────────────────
async def test_list_contracts(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA", "contract_type": "SPA"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SHA", "contract_type": "SHAREHOLDERS_AGREEMENT"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/contracts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Update ─────────────────────────────────────────────────
async def test_update_contract_status(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA"},
    )
    cid = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/contracts/{cid}",
        json={"status": "UNDER_REVIEW"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "UNDER_REVIEW"


async def test_update_contract_signatures(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA"},
    )
    cid = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/contracts/{cid}",
        json={
            "status": "PARTIALLY_SIGNED",
            "seller_signature": "SIGNED",
            "buyer_signature": "PENDING",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["seller_signature"] == "SIGNED"
    assert resp.json()["buyer_signature"] == "PENDING"


async def test_update_contract_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/contracts/{fake_id}",
        json={"status": "UNDER_REVIEW"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_contract(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA"},
    )
    cid = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/contracts/{cid}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/contracts")
    assert len(list_resp.json()) == 0


# ── Summary ────────────────────────────────────────────────
async def test_contract_summary(client):
    txn_id = await _create_txn(client)

    # SPA — DRAFT → FULLY_EXECUTED
    c1 = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA", "contract_type": "SPA"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/contracts/{c1.json()['id']}",
        json={"status": "FULLY_EXECUTED", "seller_signature": "SIGNED", "buyer_signature": "SIGNED"},
    )

    # SHA — PENDING_SIGNATURE
    c2 = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SHA", "contract_type": "SHAREHOLDERS_AGREEMENT"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/contracts/{c2.json()['id']}",
        json={"status": "PENDING_SIGNATURE"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/contracts/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["fully_executed"] == 1
    assert data["pending_signatures"] >= 1


# ── Versions ──────────────────────────────────────────────
async def test_create_and_list_versions(client):
    txn_id = await _create_txn(client)
    c = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA"},
    )
    cid = c.json()["id"]

    # 버전 추가
    v_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts/{cid}/versions",
        json={"document_url": "https://drive.google.com/file/v2", "changes_summary": "2차 수정"},
    )
    assert v_resp.status_code == 201
    assert v_resp.json()["version_number"] > 0

    # 버전 목록
    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/contracts/{cid}/versions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


# ── Analyze (Stub) ────────────────────────────────────────
async def test_analyze_contract_stub(client):
    txn_id = await _create_txn(client)
    c = await client.post(
        f"/api/v1/transactions/{txn_id}/contracts",
        json={"title": "SPA"},
    )
    cid = c.json()["id"]

    resp = await client.post(f"/api/v1/transactions/{txn_id}/contracts/{cid}/analyze")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PENDING"
    assert "clauses" in data


# ── 404 on wrong transaction ──────────────────────────────
async def test_list_contracts_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/contracts")
    assert resp.status_code == 200
    assert resp.json() == []
