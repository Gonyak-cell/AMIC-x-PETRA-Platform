"""Short-list promotion, bidding status, and buyer status regression tests."""

SAMPLE_TXN = {
    "name": "Project Alpha",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "Alpha Target",
    "client_name": "Client Corp",
    "lead_advisor_email": "advisor@example.com",
}

BUYER_WITH_CONTACT = {
    "company_name": "Buyer A",
    "contact_name": "Hong",
    "contact_email": "hong@buyer.com",
    "contact_phone": "010-1234-5678",
    "buyer_type": "STRATEGIC",
}

BUYER_NO_CONTACT = {
    "company_name": "Buyer B",
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


async def _patch_buyer(client, txn_id: str, buyer_id: str, body: dict) -> dict:
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _sign_buyer_nda(client, txn_id: str, buyer_id: str) -> dict:
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/ndas",
        json={"buyer_candidate_id": buyer_id},
    )
    assert create_resp.status_code == 201
    nda_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/ndas/{nda_id}",
        json={"status": "SIGNED", "signed_at": "2026-03-10"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _advance_to_status(client, txn_id: str, buyer_id: str, target: str) -> None:
    paths: dict[str, list[str]] = {
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
    for status in paths[target]:
        resp = await client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer_id}",
            json={"status": status},
        )
        assert resp.status_code == 200, f"Failed transition to {status}: {resp.text}"


async def test_tier_alone_does_not_auto_short_list(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"tier": "TIER_1"},
    )

    assert patched["tier"] == "TIER_1"
    assert patched["is_short_listed"] is False


async def test_status_update_to_nda_signed_auto_short_lists_with_tier(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await _patch_buyer(client, txn_id, buyer["id"], {"tier": "TIER_1"})
    await _patch_buyer(client, txn_id, buyer["id"], {"status": "CONTACTED"})
    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"status": "NDA_SIGNED"},
    )

    assert patched["status"] == "NDA_SIGNED"
    assert patched["is_short_listed"] is True


async def test_signed_nda_with_short_list_tier_auto_short_lists(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await _patch_buyer(client, txn_id, buyer["id"], {"tier": "TIER_2"})
    await _sign_buyer_nda(client, txn_id, buyer["id"])

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "NDA_SIGNED"
    assert resp.json()["is_short_listed"] is True


async def test_signed_nda_without_short_list_tier_stays_out_of_short_list(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await _sign_buyer_nda(client, txn_id, buyer["id"])

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "NDA_SIGNED"
    assert resp.json()["is_short_listed"] is False


async def test_assigning_tier_after_nda_signed_auto_short_lists(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await _sign_buyer_nda(client, txn_id, buyer["id"])
    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"tier": "TIER_3"},
    )

    assert patched["tier"] == "TIER_3"
    assert patched["is_short_listed"] is True


async def test_not_target_removes_short_list_even_after_nda_signed(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await _patch_buyer(client, txn_id, buyer["id"], {"tier": "TIER_1"})
    await _sign_buyer_nda(client, txn_id, buyer["id"])
    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"tier": "NOT_TARGET"},
    )

    assert patched["tier"] == "NOT_TARGET"
    assert patched["is_short_listed"] is False


async def test_null_tier_removes_short_list_even_after_nda_signed(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    await _patch_buyer(client, txn_id, buyer["id"], {"tier": "TIER_1"})
    await _sign_buyer_nda(client, txn_id, buyer["id"])
    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"tier": None},
    )

    assert patched["tier"] is None
    assert patched["is_short_listed"] is False


async def test_add_buyer_with_tier_stays_long_list_until_nda_signed(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers",
        json={**BUYER_NO_CONTACT, "tier": "TIER_1"},
    )
    assert resp.status_code == 201
    assert resp.json()["tier"] == "TIER_1"
    assert resp.json()["is_short_listed"] is False


async def test_is_short_listed_filter_uses_synced_membership(client):
    txn_id = await _create_txn(client)
    b1 = await _add_buyer(client, txn_id, company_name="Buyer 1")
    b2 = await _add_buyer(client, txn_id, company_name="Buyer 2")

    await _patch_buyer(client, txn_id, b1["id"], {"tier": "TIER_1"})
    await _sign_buyer_nda(client, txn_id, b1["id"])
    await _patch_buyer(client, txn_id, b2["id"], {"tier": "TIER_2"})

    resp_true = await client.get(f"/api/v1/transactions/{txn_id}/buyers?is_short_listed=true")
    assert resp_true.status_code == 200
    assert [item["id"] for item in resp_true.json()["items"]] == [b1["id"]]

    resp_false = await client.get(f"/api/v1/transactions/{txn_id}/buyers?is_short_listed=false")
    assert resp_false.status_code == 200
    returned_ids = {item["id"] for item in resp_false.json()["items"]}
    assert b1["id"] not in returned_ids
    assert b2["id"] in returned_ids


async def test_reads_repair_stale_short_list_flag_for_tiered_signed_nda(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id, company_name="Buyer synced")

    await _patch_buyer(client, txn_id, buyer["id"], {"tier": "TIER_1"})
    await _sign_buyer_nda(client, txn_id, buyer["id"])
    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"is_short_listed": False},
    )
    assert patched["is_short_listed"] is False

    detail_resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["is_short_listed"] is True

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers?is_short_listed=true")
    assert list_resp.status_code == 200
    assert [item["id"] for item in list_resp.json()["items"]] == [buyer["id"]]


async def test_new_buyer_status_values(client):
    txn_id = await _create_txn(client)

    for target in ["BID_SUBMITTED", "BID_NOT_SUBMITTED", "BID_DROPPED"]:
        buyer = await _add_buyer(client, txn_id, company_name=f"Buyer_{target}")
        await _advance_to_status(client, txn_id, buyer["id"], target)
        resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == target


async def test_bidding_summary(client):
    txn_id = await _create_txn(client)

    for i, target in enumerate(["BID_SUBMITTED", "BID_SUBMITTED", "BID_DROPPED"]):
        buyer = await _add_buyer(client, txn_id, company_name=f"Bidder{i}")
        await _advance_to_status(client, txn_id, buyer["id"], target)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers/bidding-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bidders"] == 3
    assert data["bid_submitted"] == 2
    assert data["bid_not_submitted"] == 0
    assert data["bid_dropped"] == 1


async def test_invalid_status_transition(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"status": "BID_SUBMITTED"},
    )
    assert resp.status_code == 422
    assert "상태 전이 불가" in resp.json()["detail"]


async def test_toggle_short_listed_via_patch(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"is_short_listed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is True

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"is_short_listed": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_short_listed"] is False


async def test_tier_and_status_sync_override_conflicting_short_list_payload(client):
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"tier": "TIER_1", "is_short_listed": False},
    )
    assert patched["is_short_listed"] is False

    await _patch_buyer(client, txn_id, buyer["id"], {"status": "CONTACTED"})
    patched = await _patch_buyer(
        client,
        txn_id,
        buyer["id"],
        {"status": "NDA_SIGNED", "is_short_listed": False},
    )
    assert patched["status"] == "NDA_SIGNED"
    assert patched["is_short_listed"] is True
