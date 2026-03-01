"""Short-List 승격 + 입찰 상태 + is_short_listed 필터 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 델타",
    "code_name": "DELTA-001",
    "side": "SELL",
    "target_company_name": "델타기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

BUYER_WITH_CONTACT = {
    "company_name": "매수기업A",
    "contact_name": "홍길동",
    "contact_email": "hong@buyer.com",
    "contact_phone": "010-1234-5678",
    "buyer_type": "STRATEGIC",
}

BUYER_NO_CONTACT = {
    "company_name": "매수기업B",
    "buyer_type": "FINANCIAL_SPONSOR",
}


async def _create_txn(client) -> str:
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_buyer(client, txn_id: str, **overrides) -> dict:
    body = {**BUYER_WITH_CONTACT, **overrides}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=body)
    assert resp.status_code == 201
    return resp.json()


# ── Short-List Promotion ──────────────────────────────────


async def test_promote_with_contact_info(client):
    """연락처가 있는 buyer → 승격 성공, is_short_listed=True."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": [buyer["id"]]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["is_short_listed"] is True


async def test_promote_missing_contact(client):
    """연락처 없는 buyer → 422, 누락 필드 목록."""
    txn_id = await _create_txn(client)
    # 연락처 없이 직접 생성 (BUYER_WITH_CONTACT 기본값 회피)
    resp0 = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=BUYER_NO_CONTACT)
    assert resp0.status_code == 201
    buyer = resp0.json()

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": [buyer["id"]]},
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "missing_contact" in data["detail"]


async def test_is_short_listed_default_false(client):
    """신규 buyer의 is_short_listed 기본값은 False."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    assert buyer["is_short_listed"] is False


async def test_is_short_listed_filter(client):
    """?is_short_listed=true 필터 동작 확인."""
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="기업1")
    await _add_buyer(client, txn_id, company_name="기업2")

    # b1만 승격
    await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": [b1["id"]]},
    )

    # 필터
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers?is_short_listed=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == b1["id"]


# ── Bidding Status ─────────────────────────────────────────


async def test_new_buyer_status_values(client):
    """BID_SUBMITTED/BID_NOT_SUBMITTED/BID_DROPPED 상태 사용 가능."""
    txn_id = await _create_txn(client)

    for status in ["BID_SUBMITTED", "BID_NOT_SUBMITTED", "BID_DROPPED"]:
        buyer = await _add_buyer(client, txn_id, company_name=f"기업_{status}")
        resp = await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
            json={"status": status},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == status


async def test_bidding_summary(client):
    """BID_SUBMITTED 2건, BID_DROPPED 1건 → 집계 확인."""
    txn_id = await _create_txn(client)

    # 3명의 buyer 생성 후 입찰 상태 설정
    for i, status in enumerate(["BID_SUBMITTED", "BID_SUBMITTED", "BID_DROPPED"]):
        buyer = await _add_buyer(client, txn_id, company_name=f"입찰기업{i}")
        await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
            json={"status": status},
        )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/bidding-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bidders"] == 3
    assert data["bid_submitted"] == 2
    assert data["bid_not_submitted"] == 0
    assert data["bid_dropped"] == 1


# ── is_short_listed toggle via PATCH ──────────────────────


async def test_toggle_short_listed_via_patch(client):
    """PATCH로 is_short_listed 토글 가능."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    # True로 설정
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"is_short_listed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is True

    # False로 토글
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"is_short_listed": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is False
