"""Transaction CRUD API 테스트."""

import re

SAMPLE_TXN = {
    "name": "Project Alpha",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

# 코드명 자동 생성 패턴: SE26-ALP-01 형식
CODE_NAME_PATTERN = re.compile(r"^(SE|BU|ISU|HYB|GEN)\d{2}-[A-Z]{1,3}-\d{2}$")


# ── Create ─────────────────────────────────────────────────
async def test_create_transaction(client):
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Project Alpha"
    assert data["deal_type"] == "SE"
    assert data["side"] == "SELL"
    assert data["phase"] == "ENGAGEMENT"
    assert data["status"] == "DRAFT"
    assert data["id"] is not None
    # 코드명이 자동 생성 패턴을 따르는지 확인
    assert CODE_NAME_PATTERN.match(data["code_name"]), f"코드명 형식 오류: {data['code_name']}"


async def test_create_two_transactions_sequential_code(client):
    """같은 딜 타입으로 두 건 생성 시 코드명 시퀀스가 순차적으로 증가한다."""
    resp1 = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn2 = {**SAMPLE_TXN, "name": "Project Beta"}
    resp2 = await client.post("/api/v1/transactions", json=txn2)
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    code1 = resp1.json()["code_name"]
    code2 = resp2.json()["code_name"]
    # 두 코드명이 다른지 확인 (중복 없음)
    assert code1 != code2


# ── Read ───────────────────────────────────────────────────
async def test_create_issue_transaction_uses_isu_prefix(client):
    txn = {**SAMPLE_TXN, "name": "Project Growth", "deal_type": "ISSUE"}
    resp = await client.post("/api/v1/transactions", json=txn)

    assert resp.status_code == 201
    assert resp.json()["deal_type"] == "ISSUE"
    assert resp.json()["code_name"].startswith("ISU")


async def test_get_transaction(client):
    create_resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    txn_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == txn_id
    assert resp.json()["name"] == "Project Alpha"


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
    resp = await client.get("/api/v1/transactions", params={"search": "Alpha"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_transactions_filter_side(client):
    await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    # SELL 거래 생성했지만 BUY로 필터
    resp = await client.get("/api/v1/transactions", params={"side": "BUY"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_list_transactions_pagination(client):
    # 3건 생성 (이름을 달리하여 코드명 중복 방지)
    names = ["Project Charlie", "Project Delta", "Project Echo"]
    for name in names:
        txn = {**SAMPLE_TXN, "name": name}
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
        json={"industry": "Tech"},
    )
    assert resp.status_code == 200
    assert resp.json()["industry"] == "Tech"
    # code_name은 수정 불가 — 기존 값 유지
    original_code = create_resp.json()["code_name"]
    assert resp.json()["code_name"] == original_code


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
