"""Short-List 승격 + 입찰 상태 + is_short_listed 필터 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 델타",
    "deal_type": "SE",
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


async def _advance_to_status(client, txn_id: str, buyer_id: str, target: str) -> None:
    """유효한 상태 전이 경로를 따라 buyer를 target 상태까지 이동."""
    _PATHS: dict[str, list[str]] = {
        "BID_SUBMITTED": [
            "CONTACTED",
            "NDA_SIGNED",
            "CIM_SENT",
            "INTEREST_CONFIRMED",
            "IOI_RECEIVED",
            "IOI_ACCEPTED",
            "BID_SUBMITTED",
        ],
        "BID_NOT_SUBMITTED": [
            "CONTACTED",
            "NDA_SIGNED",
            "CIM_SENT",
            "INTEREST_CONFIRMED",
            "BID_NOT_SUBMITTED",
        ],
        "BID_DROPPED": [
            "CONTACTED",
            "NDA_SIGNED",
            "CIM_SENT",
            "INTEREST_CONFIRMED",
            "IOI_RECEIVED",
            "IOI_ACCEPTED",
            "DD_GRANTED",
            "DD_IN_PROGRESS",
            "BID_DROPPED",
        ],
    }
    for s in _PATHS[target]:
        resp = await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
            json={"status": s},
        )
        assert resp.status_code == 200, f"Failed transition to {s}: {resp.text}"


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

    # is_short_listed=true 필터
    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers?is_short_listed=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == b1["id"]

    # is_short_listed=false 필터
    resp_false = await client.get(f"/api/v1/transactions/{txn_id}/buyers?is_short_listed=false")
    assert resp_false.status_code == 200
    data_false = resp_false.json()
    assert len(data_false) == 1
    assert data_false[0]["is_short_listed"] is False


# ── Bidding Status ─────────────────────────────────────────


async def test_new_buyer_status_values(client):
    """BID_SUBMITTED/BID_NOT_SUBMITTED/BID_DROPPED 상태 사용 가능."""
    txn_id = await _create_txn(client)

    for target in ["BID_SUBMITTED", "BID_NOT_SUBMITTED", "BID_DROPPED"]:
        buyer = await _add_buyer(client, txn_id, company_name=f"기업_{target}")
        await _advance_to_status(client, txn_id, buyer["id"], target)
        # 최종 상태 확인
        resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == target


async def test_bidding_summary(client):
    """BID_SUBMITTED 2건, BID_DROPPED 1건 → 집계 확인."""
    txn_id = await _create_txn(client)

    # 3명의 buyer 생성 후 유효한 전이 경로를 통해 입찰 상태 설정
    for i, target in enumerate(["BID_SUBMITTED", "BID_SUBMITTED", "BID_DROPPED"]):
        buyer = await _add_buyer(client, txn_id, company_name=f"입찰기업{i}")
        await _advance_to_status(client, txn_id, buyer["id"], target)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/bidding-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bidders"] == 3
    assert data["bid_submitted"] == 2
    assert data["bid_not_submitted"] == 0
    assert data["bid_dropped"] == 1


# ── Status Transition Validation ──────────────────────────


async def test_invalid_status_transition(client):
    """IDENTIFIED → BID_SUBMITTED 직접 전이 → 422."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "BID_SUBMITTED"},
    )
    assert resp.status_code == 422
    assert "상태 전이 불가" in resp.json()["detail"]


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


# ── Boundary / Edge-case Tests ────────────────────────────


async def test_promote_empty_buyer_ids(client):
    """빈 buyer_ids 목록 → 빈 결과 (에러 아님)."""
    txn_id = await _create_txn(client)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": []},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_promote_already_promoted(client):
    """이미 Short-List인 buyer 재승격 → 멱등 성공."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    # 첫 번째 승격
    resp1 = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": [buyer["id"]]},
    )
    assert resp1.status_code == 200

    # 두 번째 승격 (멱등)
    resp2 = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": [buyer["id"]]},
    )
    assert resp2.status_code == 200
    assert resp2.json()[0]["is_short_listed"] is True


async def test_promote_partial_contact_failure(client):
    """일부 buyer만 연락처 누락 → 전체 422 (부분 승격 불가)."""
    txn_id = await _create_txn(client)

    # 연락처 있는 buyer
    b_ok = await _add_buyer(client, txn_id, company_name="연락처있음")

    # 연락처 없는 buyer
    resp_no = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=BUYER_NO_CONTACT)
    assert resp_no.status_code == 201
    b_no = resp_no.json()

    # 둘 다 동시 승격 시도 → 연락처 없는 buyer 때문에 422
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/promote-short-list",
        json={"buyer_ids": [b_ok["id"], b_no["id"]]},
    )
    assert resp.status_code == 422
    assert "missing_contact" in resp.json()["detail"]
