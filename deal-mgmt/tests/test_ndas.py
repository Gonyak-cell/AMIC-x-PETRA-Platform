"""NDA 관리 API 테스트."""

SAMPLE_TXN = {
    "name": "NDA 테스트 거래",
    "code_name": "NDA-001",
    "side": "SELL",
    "target_company_name": "NDA기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_BUYER = {
    "company_name": "삼성물산",
    "buyer_type": "STRATEGIC",
}


async def _create_txn_and_buyer(client) -> tuple[str, str]:
    txn_resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn_id = txn_resp.json()["id"]
    buyer_resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=SAMPLE_BUYER)
    buyer_id = buyer_resp.json()["id"]
    return txn_id, buyer_id


# ── Create ─────────────────────────────────────────────────
async def test_create_nda(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer_id, "nda_type": "MUTUAL", "expires_at": "2027-01-15"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nda_type"] == "MUTUAL"
    assert data["status"] == "DRAFT"
    assert data["buyer_candidate_id"] == buyer_id


async def test_create_nda_one_way(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer_id, "nda_type": "ONE_WAY"},
    )
    assert resp.status_code == 201
    assert resp.json()["nda_type"] == "ONE_WAY"


# ── List / Filter ──────────────────────────────────────────
async def test_list_ndas(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    await client.post(f"/api/v1/transactions/{txn_id}/ndas", json={"buyer_candidate_id": buyer_id})

    buyer2_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={"company_name": "SK텔레콤", "buyer_type": "STRATEGIC"},
    )
    buyer2_id = buyer2_resp.json()["id"]
    await client.post(f"/api/v1/transactions/{txn_id}/ndas", json={"buyer_candidate_id": buyer2_id})

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ndas")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_ndas_filter_buyer(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    await client.post(f"/api/v1/transactions/{txn_id}/ndas", json={"buyer_candidate_id": buyer_id})

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ndas", params={"buyer_id": buyer_id})
    assert len(resp.json()) == 1


# ── Update ─────────────────────────────────────────────────
async def test_update_nda_status(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer_id},
    )
    nda_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/ndas/{nda_id}",
        json={"status": "SENT", "sent_at": "2026-03-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SENT"
    assert resp.json()["sent_at"] == "2026-03-01"


async def test_update_nda_signed(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer_id},
    )
    nda_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/ndas/{nda_id}",
        json={"status": "SIGNED", "signed_at": "2026-03-10"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SIGNED"


async def test_update_nda_404(client):
    txn_id, _ = await _create_txn_and_buyer(client)
    fake_nda = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/ndas/{fake_nda}",
        json={"status": "SENT"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_nda(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer_id},
    )
    nda_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/ndas/{nda_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/ndas")
    assert len(list_resp.json()) == 0


# ── Summary ────────────────────────────────────────────────
async def test_nda_summary(client):
    txn_id, buyer_id = await _create_txn_and_buyer(client)

    # NDA 2개 생성: 1개 SIGNED, 1개 SENT
    nda1 = await client.post(f"/api/v1/transactions/{txn_id}/ndas", json={"buyer_candidate_id": buyer_id})
    await client.patch(
        f"/api/v1/transactions/{txn_id}/ndas/{nda1.json()['id']}",
        json={"status": "SIGNED"},
    )

    buyer2 = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={"company_name": "MBK Partners", "buyer_type": "FINANCIAL_SPONSOR"},
    )
    nda2 = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer2.json()["id"]},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/ndas/{nda2.json()['id']}",
        json={"status": "SENT"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/ndas/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["signed_count"] == 1
    assert data["pending_count"] == 1
