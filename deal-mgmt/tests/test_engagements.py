"""Engagement + Working Group + Conflict Check API 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 감마",
    "code_name": "GAMMA-001",
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


# ── Conflict Check ──────────────────────────────────────────
async def test_conflict_check_no_conflict(client):
    txn_id = await _create_txn(client)
    # ACTIVE로 전환
    await client.post(f"/api/v1/transactions/{txn_id}/workflow/status", json={"to_status": "ACTIVE"})

    resp = await client.get(f"/api/v1/transactions/{txn_id}/conflict-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_conflicts"] is False
    assert data["conflicts"] == []


async def test_conflict_check_same_company_name(client):
    """동일 대상기업 — ACTIVE 거래 존재 시 CRITICAL."""
    txn1_id = await _create_txn(client)
    resp_s = await client.post(f"/api/v1/transactions/{txn1_id}/workflow/status", json={"to_status": "ACTIVE"})
    assert resp_s.status_code == 200

    txn2_id = await _create_txn(client, code_name="GAMMA-002", name="프로젝트 감마2")
    resp = await client.get(f"/api/v1/transactions/{txn2_id}/conflict-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_conflicts"] is True
    assert len(data["conflicts"]) == 1
    assert data["conflicts"][0]["severity"] == "CRITICAL"


async def test_conflict_check_draft_company(client):
    """동일 대상기업 — DRAFT 거래 존재 시 WARNING."""
    await _create_txn(client)  # DRAFT 상태
    txn2_id = await _create_txn(client, code_name="GAMMA-002", name="프로젝트 감마2")

    resp = await client.get(f"/api/v1/transactions/{txn2_id}/conflict-check")
    data = resp.json()
    assert data["has_conflicts"] is True
    assert data["conflicts"][0]["severity"] == "WARNING"


async def test_conflict_check_same_corp_code(client):
    """동일 corp_code — 회사명 다르지만 corp_code 일치 시 WARNING."""
    txn1_id = await _create_txn(client, target_company_name="회사A")
    await client.patch(f"/api/v1/transactions/{txn1_id}", json={"target_corp_code": "00123456"})

    txn2_id = await _create_txn(
        client,
        code_name="GAMMA-002",
        name="프로젝트 감마2",
        target_company_name="회사B",
    )
    await client.patch(f"/api/v1/transactions/{txn2_id}", json={"target_corp_code": "00123456"})

    resp = await client.get(f"/api/v1/transactions/{txn2_id}/conflict-check")
    data = resp.json()
    assert data["has_conflicts"] is True
    assert any(c["severity"] == "WARNING" for c in data["conflicts"])
