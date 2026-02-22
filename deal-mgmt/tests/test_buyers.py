"""Buyer Candidate Pipeline API 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 델타",
    "code_name": "DELTA-001",
    "side": "SELL",
    "target_company_name": "델타기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_BUYER = {
    "company_name": "삼성물산",
    "contact_name": "이매수",
    "contact_email": "lee@samsung.com",
    "contact_phone": "02-9999-1234",
    "buyer_type": "STRATEGIC",
    "notes": "전략적 시너지 높음",
}


# ── Helper ─────────────────────────────────────────────────
async def _create_txn(client, **overrides) -> str:
    body = {**SAMPLE_TXN, **overrides}
    resp = await client.post("/api/v1/transactions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_buyer(client, txn_id: str, **overrides) -> dict:
    body = {**SAMPLE_BUYER, **overrides}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=body)
    assert resp.status_code == 201
    return resp.json()


# ── Create ─────────────────────────────────────────────────
async def test_add_buyer(client):
    txn_id = await _create_txn(client)
    data = await _add_buyer(client, txn_id)
    assert data["company_name"] == "삼성물산"
    assert data["buyer_type"] == "STRATEGIC"
    assert data["status"] == "IDENTIFIED"
    assert data["transaction_id"] == txn_id


async def test_add_buyer_financial_sponsor(client):
    txn_id = await _create_txn(client)
    data = await _add_buyer(
        client,
        txn_id,
        company_name="MBK Partners",
        buyer_type="FINANCIAL_SPONSOR",
    )
    assert data["buyer_type"] == "FINANCIAL_SPONSOR"


async def test_add_buyer_invalid_txn(client):
    fake_txn = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/v1/transactions/{fake_txn}/buyers", json=SAMPLE_BUYER)
    assert resp.status_code == 404


# ── Read / List ────────────────────────────────────────────
async def test_get_buyer(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
    assert resp.status_code == 200
    assert resp.json()["company_name"] == "삼성물산"


async def test_get_buyer_404(client):
    txn_id = await _create_txn(client)
    fake_buyer = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{fake_buyer}")
    assert resp.status_code == 404


async def test_list_buyers(client):
    txn_id = await _create_txn(client)
    await _add_buyer(client, txn_id)
    await _add_buyer(client, txn_id, company_name="SK텔레콤", contact_email="sk@skt.co.kr")

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_buyers_filter_status(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    # 상태를 NDA_SENT로 변경
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "NDA_SENT"},
    )

    # IDENTIFIED 필터 → 0건
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers", params={"status": "IDENTIFIED"})
    assert len(resp.json()) == 0

    # NDA_SENT 필터 → 1건
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers", params={"status": "NDA_SENT"})
    assert len(resp.json()) == 1


async def test_list_buyers_filter_type(client):
    txn_id = await _create_txn(client)
    await _add_buyer(client, txn_id)
    await _add_buyer(client, txn_id, company_name="MBK Partners", buyer_type="FINANCIAL_SPONSOR")

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers", params={"type": "STRATEGIC"})
    assert len(resp.json()) == 1
    assert resp.json()[0]["company_name"] == "삼성물산"


# ── Update ─────────────────────────────────────────────────
async def test_update_buyer_status(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "NDA_SENT"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "NDA_SENT"


async def test_update_buyer_ioi(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={
            "status": "IOI_RECEIVED",
            "ioi_value": 50000000000,
            "ioi_date": "2026-03-15",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ioi_value"] == 50000000000
    assert resp.json()["ioi_date"] == "2026-03-15"
    assert resp.json()["status"] == "IOI_RECEIVED"


async def test_update_buyer_loi(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={
            "status": "LOI_RECEIVED",
            "loi_value": 55000000000,
            "loi_date": "2026-04-01",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["loi_value"] == 55000000000


async def test_update_buyer_rejection(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "REJECTED", "rejection_reason": "가격 조건 불일치"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["rejection_reason"] == "가격 조건 불일치"


async def test_update_buyer_404(client):
    txn_id = await _create_txn(client)
    fake_buyer = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{fake_buyer}",
        json={"notes": "없는 매수자"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_remove_buyer(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
    assert resp.status_code == 204

    # 삭제 후 목록에서 제외
    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers")
    assert len(list_resp.json()) == 0


async def test_remove_buyer_404(client):
    txn_id = await _create_txn(client)
    fake_buyer = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/transactions/{txn_id}/buyers/{fake_buyer}")
    assert resp.status_code == 404


# ── Pipeline Summary ───────────────────────────────────────
async def test_buyer_summary_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["by_status"] == {}
    assert data["avg_ioi_value"] is None


async def test_buyer_summary_with_data(client):
    txn_id = await _create_txn(client)

    # 3명의 매수자 추가
    b1 = await _add_buyer(client, txn_id)
    b2 = await _add_buyer(client, txn_id, company_name="SK텔레콤")
    b3 = await _add_buyer(client, txn_id, company_name="MBK Partners", buyer_type="FINANCIAL_SPONSOR")

    # b1: IOI 수령
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}",
        json={"status": "IOI_RECEIVED", "ioi_value": 50000000000},
    )
    # b2: IOI 수령
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b2['id']}",
        json={"status": "IOI_RECEIVED", "ioi_value": 60000000000},
    )
    # b3: NDA 발송
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b3['id']}",
        json={"status": "NDA_SENT"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/summary")
    data = resp.json()
    assert data["total"] == 3
    assert data["by_status"]["IOI_RECEIVED"] == 2
    assert data["by_status"]["NDA_SENT"] == 1
    assert data["avg_ioi_value"] == 55000000000
    assert data["avg_loi_value"] is None
