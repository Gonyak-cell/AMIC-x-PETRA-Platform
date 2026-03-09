"""Tier 기반 Short-List 자동 승격 + 입찰 상태 + 필터 테스트."""

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


# ── Tier 기반 Short-List 자동 승격 ─────────────────────────


async def test_tier_1_auto_short_list(client):
    """Tier 1 설정 → is_short_listed=True 자동 승격."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    assert buyer["is_short_listed"] is False

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_1"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is True
    assert resp.json()["tier"] == "TIER_1"


async def test_tier_2_auto_short_list(client):
    """Tier 2 설정 → is_short_listed=True 자동 승격."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_2"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is True


async def test_tier_3_auto_short_list(client):
    """Tier 3 설정 → is_short_listed=True 자동 승격."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_3"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is True


async def test_not_target_removes_short_list(client):
    """NOT_TARGET 설정 → is_short_listed=False 자동 해제."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    # 먼저 Tier 1로 승격
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_1"},
    )

    # NOT_TARGET으로 변경 → Short List 해제
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "NOT_TARGET"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is False
    assert resp.json()["tier"] == "NOT_TARGET"


async def test_null_tier_removes_short_list(client):
    """Tier를 null로 설정 → is_short_listed=False 자동 해제."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    # 먼저 Tier 1로 승격
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_1"},
    )

    # Tier null로 변경 → Short List 해제
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": None},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is False
    assert resp.json()["tier"] is None


async def test_no_contact_required_for_short_list(client):
    """연락처 없이 Tier 1 설정 → 성공 (422 아님)."""
    txn_id = await _create_txn(client)
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=BUYER_NO_CONTACT)
    assert resp.status_code == 201
    buyer = resp.json()

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_1"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is True


async def test_add_buyer_with_tier_auto_short_list(client):
    """POST 생성 시 tier=TIER_1 → is_short_listed=True 자동 설정."""
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={**BUYER_NO_CONTACT, "tier": "TIER_1"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_short_listed"] is True
    assert resp.json()["tier"] == "TIER_1"


async def test_add_buyer_without_tier_not_short_listed(client):
    """POST 생성 시 tier 미지정 → is_short_listed=False 기본값."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)
    assert buyer["is_short_listed"] is False


# ── is_short_listed 필터 ─────────────────────────────────


async def test_is_short_listed_filter(client):
    """?is_short_listed=true 필터 동작 확인."""
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="기업1")
    await _add_buyer(client, txn_id, company_name="기업2")

    # b1만 Tier 1로 승격
    await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{b1['id']}",
        json={"tier": "TIER_1"},
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
    """PATCH로 is_short_listed 직접 토글 가능 (Tier 없이)."""
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


async def test_tier_overrides_is_short_listed_mismatch(client):
    """Tier + is_short_listed 동시 PATCH 시 Tier가 우선한다."""
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    # Tier=TIER_1 + is_short_listed=False 동시 전송 → Tier 우선 → True
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "TIER_1", "is_short_listed": False},
    )
    assert resp.status_code == 200
    assert resp.json()["tier"] == "TIER_1"
    assert resp.json()["is_short_listed"] is True

    # Tier=NOT_TARGET + is_short_listed=True 동시 전송 → Tier 우선 → False
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"tier": "NOT_TARGET", "is_short_listed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["tier"] == "NOT_TARGET"
    assert resp.json()["is_short_listed"] is False
