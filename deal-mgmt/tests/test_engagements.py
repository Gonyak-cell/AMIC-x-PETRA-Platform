"""Engagement + Working Group API 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 감마",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "감마기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_ENGAGEMENT = {
    "type": "EXCLUSIVE",
    "fee_structure": {"retainer": 50000, "success_pct": 2.0},
    "signed_at": "2026-01-15",
    "expires_at": "2027-01-15",
    "notes": "독점 자문 계약",
}

SAMPLE_MEMBER = {
    "name": "김변호사",
    "deal_type": "SE",
    "email": "kim@lawfirm.co.kr",
    "organization": "김앤장 법률사무소",
    "role": "LEGAL_COUNSEL",
    "phone": "02-1234-5678",
}


# ── Helper ─────────────────────────────────────────────────
async def _create_txn(client, **overrides) -> str:
    body = {**SAMPLE_TXN, **overrides}
    resp = await client.post("/api/v1/transactions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Engagement CRUD ────────────────────────────────────────
async def test_create_engagement(client):
    txn_id = await _create_txn(client)
    resp = await client.post(f"/api/v1/transactions/{txn_id}/engagements", json=SAMPLE_ENGAGEMENT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "EXCLUSIVE"
    assert data["fee_structure"]["success_pct"] == 2.0
    assert data["signed_at"] == "2026-01-15"
    assert data["transaction_id"] == txn_id


async def test_list_engagements(client):
    txn_id = await _create_txn(client)
    await client.post(f"/api/v1/transactions/{txn_id}/engagements", json=SAMPLE_ENGAGEMENT)
    await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json={**SAMPLE_ENGAGEMENT, "type": "CO_ADVISORY"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/engagements")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_engagement(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(f"/api/v1/transactions/{txn_id}/engagements", json=SAMPLE_ENGAGEMENT)
    eng_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/engagements/{eng_id}",
        json={"type": "NON_EXCLUSIVE", "notes": "비독점으로 변경"},
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "NON_EXCLUSIVE"
    assert resp.json()["notes"] == "비독점으로 변경"


async def test_delete_engagement(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(f"/api/v1/transactions/{txn_id}/engagements", json=SAMPLE_ENGAGEMENT)
    eng_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/engagements/{eng_id}")
    assert resp.status_code == 204

    # 삭제 후 목록에서 제외
    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/engagements")
    assert len(list_resp.json()) == 0


async def test_engagement_404_invalid_txn(client):
    fake_txn = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/v1/transactions/{fake_txn}/engagements", json=SAMPLE_ENGAGEMENT)
    assert resp.status_code == 404


async def test_engagement_update_404(client):
    txn_id = await _create_txn(client)
    fake_eng = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/engagements/{fake_eng}",
        json={"notes": "없는 수임계약"},
    )
    assert resp.status_code == 404


# ── Working Group CRUD ──────────────────────────────────────
async def test_add_member(client):
    txn_id = await _create_txn(client)
    resp = await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "김변호사"
    assert data["role"] == "LEGAL_COUNSEL"
    assert data["is_active"] is True


async def test_list_members(client):
    txn_id = await _create_txn(client)
    await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json={**SAMPLE_MEMBER, "name": "박회계사", "email": "park@accounting.co.kr", "role": "ACCOUNTING_ADVISOR"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/members")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_member(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    member_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{member_id}",
        json={"organization": "법무법인 세종", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["organization"] == "법무법인 세종"
    assert resp.json()["is_active"] is False


async def test_remove_member(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    member_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/members/{member_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/members")
    assert len(list_resp.json()) == 0


async def test_duplicate_member_email(client):
    txn_id = await _create_txn(client)
    await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    resp = await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    assert resp.status_code == 409


async def test_member_404(client):
    txn_id = await _create_txn(client)
    fake_member = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{fake_member}",
        json={"name": "없는 멤버"},
    )
    assert resp.status_code == 404
