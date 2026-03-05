"""Closing 체크리스트 API 테스트."""

SAMPLE_TXN = {
    "name": "Closing 테스트 거래",
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
async def test_create_closing_item(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={
            "category": "REGULATORY",
            "title": "공정거래위원회 기업결합신고",
            "responsible_party": "법률자문팀",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "REGULATORY"
    assert data["title"] == "공정거래위원회 기업결합신고"
    assert data["status"] == "PENDING"
    assert data["responsible_party"] == "법률자문팀"


async def test_create_closing_item_minimal(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "LEGAL", "title": "SPA 체결"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING"


# ── List / Filter ──────────────────────────────────────────
async def test_list_closing_items(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "REGULATORY", "title": "기업결합신고"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "FINANCIAL", "title": "에스크로 입금"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "REGULATORY", "title": "산업통상자원부 신고"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/closing")
    assert resp.status_code == 200
    # 거래 생성 시 표준 15개 항목이 자동 생성되므로 15 + 3 = 18
    assert len(resp.json()) == 18


async def test_list_closing_filter_category(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "REGULATORY", "title": "기업결합신고"},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "FINANCIAL", "title": "에스크로"},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/closing",
        params={"category": "REGULATORY"},
    )
    assert resp.status_code == 200
    # 자동 생성 REGULATORY 2개 + 수동 1개 = 3개
    assert len(resp.json()) == 3
    assert all(item["category"] == "REGULATORY" for item in resp.json())


# ── Update ─────────────────────────────────────────────────
async def test_update_closing_status(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "LEGAL", "title": "SPA 체결"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/closing/{item_id}",
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"


async def test_update_closing_completed(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "REGULATORY", "title": "기업결합신고"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/closing/{item_id}",
        json={"status": "COMPLETED", "completed_date": "2026-06-15"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    assert resp.json()["completed_date"] == "2026-06-15"


async def test_update_closing_404(client):
    txn_id = await _create_txn(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/closing/{fake_id}",
        json={"status": "IN_PROGRESS"},
    )
    assert resp.status_code == 404


# ── Delete ─────────────────────────────────────────────────
async def test_delete_closing_item(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "LEGAL", "title": "SPA 체결"},
    )
    item_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/closing/{item_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/closing")
    # 수동 1개 삭제 후 자동 생성 15개만 남음
    assert len(list_resp.json()) == 15


# ── Summary ────────────────────────────────────────────────
async def test_closing_summary(client):
    txn_id = await _create_txn(client)

    # 3개 항목: 1 COMPLETED, 1 IN_PROGRESS, 1 PENDING
    c1 = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "REGULATORY", "title": "기업결합신고"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/closing/{c1.json()['id']}",
        json={"status": "COMPLETED"},
    )

    c2 = await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "LEGAL", "title": "SPA 체결"},
    )
    await client.patch(
        f"/api/v1/transactions/{txn_id}/closing/{c2.json()['id']}",
        json={"status": "IN_PROGRESS"},
    )

    await client.post(
        f"/api/v1/transactions/{txn_id}/closing",
        json={"category": "FINANCIAL", "title": "에스크로"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/closing/summary")
    assert resp.status_code == 200
    data = resp.json()
    # 자동 15개 + 수동 3개 = 18, 완료 1개 → 1/18 ≈ 0.056
    assert data["total"] == 18
    assert 0.05 <= data["completion_rate"] <= 0.06


async def test_closing_summary_empty(client):
    txn_id = await _create_txn(client)
    resp = await client.get(f"/api/v1/transactions/{txn_id}/closing/summary")
    assert resp.status_code == 200
    data = resp.json()
    # 거래 생성 시 표준 15개가 자동 생성되므로 total == 15
    assert data["total"] == 15
    assert data["completion_rate"] == 0
