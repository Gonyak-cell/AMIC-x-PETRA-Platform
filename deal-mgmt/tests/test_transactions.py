"""Transaction CRUD API 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 알파",
    "code_name": "ALPHA-001",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


# ── Create ─────────────────────────────────────────────────
async def test_create_transaction(client):
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "프로젝트 알파"
    assert data["code_name"] == "ALPHA-001"
    assert data["side"] == "SELL"
    assert data["phase"] == "ENGAGEMENT"
    assert data["status"] == "DRAFT"
    assert data["id"] is not None


async def test_create_duplicate_code_name(client):
    await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 409


# ── Read ───────────────────────────────────────────────────
async def test_get_transaction(client):
    create_resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == txn_id
    assert resp.json()["name"] == "프로젝트 알파"


async def test_get_nonexistent_transaction(client):
    resp = await client.get("/api/v1/transactions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ── List ───────────────────────────────────────────────────
async def test_list_transactions(client):
    await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    resp = await client.get("/api/v1/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


async def test_list_transactions_search(client):
    await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    resp = await client.get("/api/v1/transactions", params={"search": "알파"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_transactions_filter_side(client):
    await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    # SELL 거래 생성했지만 BUY로 필터
    resp = await client.get("/api/v1/transactions", params={"side": "BUY"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_list_transactions_pagination(client):
    # 3건 생성
    for i in range(3):
        txn = {**SAMPLE_TXN, "code_name": f"PAGE-{i:03d}", "name": f"거래 {i}"}
        await client.post("/api/v1/transactions", json=txn)

    resp = await client.get("/api/v1/transactions", params={"limit": 2, "offset": 0})
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2

    resp2 = await client.get("/api/v1/transactions", params={"limit": 2, "offset": 2})
    assert len(resp2.json()["items"]) == 1


# ── Update ─────────────────────────────────────────────────
async def test_update_transaction(client):
    create_resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}",
        json={"name": "프로젝트 베타", "industry": "Tech"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "프로젝트 베타"
    assert resp.json()["industry"] == "Tech"


async def test_update_code_name_duplicate(client):
    await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn2 = {**SAMPLE_TXN, "code_name": "BETA-001", "name": "프로젝트 베타"}
    resp2 = await client.post("/api/v1/transactions", json=txn2)
    txn2_id = resp2.json()["id"]

    # BETA-001 → ALPHA-001 (이미 존재)
    resp = await client.patch(
        f"/api/v1/transactions/{txn2_id}",
        json={"code_name": "ALPHA-001"},
    )
    assert resp.status_code == 409


# ── Delete (Soft) ──────────────────────────────────────────
async def test_delete_transaction(client):
    create_resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}")
    assert resp.status_code == 204

    # 삭제 후 조회 시 404
    resp = await client.get(f"/api/v1/transactions/{txn_id}")
    assert resp.status_code == 404

    # 목록에서도 제외
    resp = await client.get("/api/v1/transactions")
    assert resp.json()["total"] == 0
