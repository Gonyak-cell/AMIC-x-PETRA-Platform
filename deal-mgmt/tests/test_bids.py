"""Bid (IOI/LOI/Final Offer) API 테스트."""

SAMPLE_TXN = {
    "name": "입찰 테스트 거래",
    "code_name": "BID-001",
    "side": "SELL",
    "target_company_name": "입찰기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_BUYER = {"company_name": "삼성물산", "buyer_type": "STRATEGIC"}


async def _setup(client) -> tuple[str, str]:
    txn = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn_id = txn.json()["id"]
    buyer = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=SAMPLE_BUYER)
    return txn_id, buyer.json()["id"]


# ── Create ─────────────────────────────────────────────────
async def test_create_ioi(client):
    txn_id, buyer_id = await _setup(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_id,
            "bid_type": "IOI",
            "amount": 50000000000,
            "valuation_method": "EV_EBITDA",
            "multiple": 8.5,
            "submitted_at": "2026-03-15",
            "valid_until": "2026-04-15",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["bid_type"] == "IOI"
    assert data["amount"] == 50000000000
    assert data["valuation_method"] == "EV_EBITDA"
    assert data["multiple"] == 8.5
    assert data["status"] == "SUBMITTED"


async def test_create_loi(client):
    txn_id, buyer_id = await _setup(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_id,
            "bid_type": "LOI",
            "amount": 55000000000,
            "conditions": "DD 결과 기반 가격 조정 조항",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["bid_type"] == "LOI"


# ── List / Filter ──────────────────────────────────────────
async def test_list_bids(client):
    txn_id, buyer_id = await _setup(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI", "amount": 50000000000},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI", "amount": 55000000000},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/bids")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_bids_filter_type(client):
    txn_id, buyer_id = await _setup(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/bids", params={"type": "IOI"})
    assert len(resp.json()) == 1
    assert resp.json()[0]["bid_type"] == "IOI"


# ── Update ─────────────────────────────────────────────────
async def test_update_bid_status(client):
    txn_id, buyer_id = await _setup(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI", "amount": 50000000000},
    )
    bid_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/bids/{bid_id}",
        json={"status": "ACCEPTED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"


async def test_update_bid_amount(client):
    txn_id, buyer_id = await _setup(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI", "amount": 50000000000},
    )
    bid_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/bids/{bid_id}",
        json={"amount": 52000000000, "notes": "가격 재협상"},
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 52000000000


async def test_update_bid_404(client):
    txn_id, _ = await _setup(client)
    fake_bid = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/bids/{fake_bid}",
        json={"status": "ACCEPTED"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_bid(client):
    txn_id, buyer_id = await _setup(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI"},
    )
    bid_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/bids/{bid_id}")
    assert resp.status_code == 204


# ── Comparison Matrix ──────────────────────────────────────
async def test_bid_comparison_matrix(client):
    txn_id, buyer1_id = await _setup(client)

    # 2번째 매수자
    buyer2 = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={"company_name": "MBK Partners", "buyer_type": "FINANCIAL_SPONSOR"},
    )
    buyer2_id = buyer2.json()["id"]

    # buyer1: IOI + LOI
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer1_id, "bid_type": "IOI", "amount": 50000000000},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer1_id, "bid_type": "LOI", "amount": 55000000000},
    )

    # buyer2: IOI만
    await client.post(
        f"/api/v1/transactions/{txn_id}/bids",
        json={"buyer_candidate_id": buyer2_id, "bid_type": "IOI", "amount": 48000000000},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/bids/comparison")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # buyer1: IOI + LOI
    b1 = next(d for d in data if d["buyer_name"] == "삼성물산")
    assert b1["ioi"] is not None
    assert b1["ioi"]["amount"] == 50000000000
    assert b1["loi"] is not None
    assert b1["loi"]["amount"] == 55000000000
    assert b1["final_offer"] is None

    # buyer2: IOI만
    b2 = next(d for d in data if d["buyer_name"] == "MBK Partners")
    assert b2["ioi"] is not None
    assert b2["loi"] is None
