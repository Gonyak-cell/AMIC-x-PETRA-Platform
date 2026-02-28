"""컨소시엄/공동투자 매핑 CRUD + deal_role + created_by_email 테스트."""

SAMPLE_TXN = {
    "name": "프로젝트 델타",
    "code_name": "DELTA-001",
    "side": "SELL",
    "target_company_name": "델타기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


async def _create_txn(client, **overrides) -> str:
    body = {**SAMPLE_TXN, **overrides}
    resp = await client.post("/api/v1/transactions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_buyer(client, txn_id: str, **overrides) -> dict:
    body = {"company_name": "기본기업", "buyer_type": "STRATEGIC", **overrides}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=body)
    assert resp.status_code == 201
    return resp.json()


# ── Consortium CRUD ───────────────────────────────────────


async def test_create_consortium_mapping(client) -> None:
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드투자")
    co = await _add_buyer(client, txn_id, company_name="공동투자")

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={
            "lead_buyer_id": lead["id"],
            "co_investor_buyer_id": co["id"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["lead_buyer_name"] == "리드투자"
    assert data["co_investor_buyer_name"] == "공동투자"
    assert data["status"] == "TAPPING"
    assert data["equity_share_pct"] is None


async def test_self_reference_rejected(client) -> None:
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id, company_name="자기참조")

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={
            "lead_buyer_id": buyer["id"],
            "co_investor_buyer_id": buyer["id"],
        },
    )
    assert resp.status_code == 422


async def test_duplicate_pair_rejected(client) -> None:
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드")
    co = await _add_buyer(client, txn_id, company_name="코인")

    resp1 = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={
            "lead_buyer_id": lead["id"],
            "co_investor_buyer_id": co["id"],
        },
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={
            "lead_buyer_id": lead["id"],
            "co_investor_buyer_id": co["id"],
        },
    )
    assert resp2.status_code == 409


async def test_cross_txn_buyer_rejected(client) -> None:
    txn1 = await _create_txn(client, code_name="T1")
    txn2 = await _create_txn(client, code_name="T2")
    lead = await _add_buyer(client, txn1, company_name="A")
    co = await _add_buyer(client, txn2, company_name="B")

    resp = await client.post(
        f"/api/v1/transactions/{txn1}/consortium/",
        json={
            "lead_buyer_id": lead["id"],
            "co_investor_buyer_id": co["id"],
        },
    )
    assert resp.status_code == 404


async def test_update_status(client) -> None:
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드")
    co = await _add_buyer(client, txn_id, company_name="코인")

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={
            "lead_buyer_id": lead["id"],
            "co_investor_buyer_id": co["id"],
        },
    )
    mapping_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"status": "CONFIRMED", "equity_share_pct": 30.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFIRMED"
    assert data["equity_share_pct"] == "30.00"


async def test_delete_mapping(client) -> None:
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드")
    co = await _add_buyer(client, txn_id, company_name="코인")

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={
            "lead_buyer_id": lead["id"],
            "co_investor_buyer_id": co["id"],
        },
    )
    mapping_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
    )
    assert resp.status_code == 204


async def test_multi_tapping(client) -> None:
    """동일 co-investor가 여러 lead와 동시 TAPPING 가능."""
    txn_id = await _create_txn(client)
    lead1 = await _add_buyer(client, txn_id, company_name="리드1")
    lead2 = await _add_buyer(client, txn_id, company_name="리드2")
    co = await _add_buyer(client, txn_id, company_name="공동")

    resp1 = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead1["id"], "co_investor_buyer_id": co["id"]},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead2["id"], "co_investor_buyer_id": co["id"]},
    )
    assert resp2.status_code == 201


async def test_list_includes_buyer_names(client) -> None:
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="주도기업")
    co = await _add_buyer(client, txn_id, company_name="참여기업")

    await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co["id"]},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/consortium/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["lead_buyer_name"] == "주도기업"
    assert data[0]["co_investor_buyer_name"] == "참여기업"


async def test_buyer_summary(client) -> None:
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="A")
    co1 = await _add_buyer(client, txn_id, company_name="B")
    co2 = await _add_buyer(client, txn_id, company_name="C")

    await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co1["id"]},
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co2["id"]},
    )

    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/consortium/summary/{lead['id']}",
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Deal Role ─────────────────────────────────────────────


async def test_create_buyer_with_deal_role(client) -> None:
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(
        client,
        txn_id,
        company_name="역할부여",
        deal_role="CONSORTIUM_LEAD",
    )
    assert buyer["deal_role"] == "CONSORTIUM_LEAD"


async def test_update_deal_role(client) -> None:
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id, company_name="역할변경")
    assert buyer["deal_role"] is None

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        json={"deal_role": "CO_INVESTOR"},
    )
    assert resp.status_code == 200
    assert resp.json()["deal_role"] == "CO_INVESTOR"


async def test_list_includes_deal_role(client) -> None:
    txn_id = await _create_txn(client)
    await _add_buyer(
        client,
        txn_id,
        company_name="단독",
        deal_role="SOLE_BUYER",
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/buyers")
    assert resp.status_code == 200
    data = resp.json()
    assert any(b["deal_role"] == "SOLE_BUYER" for b in data)


# ── Created By Email ──────────────────────────────────────


async def test_sole_buyer_consortium_rejected(client) -> None:
    """SOLE_BUYER는 컨소시엄 매핑 불가."""
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드", deal_role="SOLE_BUYER")
    co = await _add_buyer(client, txn_id, company_name="코인")

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co["id"]},
    )
    assert resp.status_code == 422
    assert "단독 매수자" in resp.json()["detail"]


async def test_status_transition_rejected(client) -> None:
    """무효한 상태 전이 거부 — CONFIRMED→TAPPING, DROPPED→CONFIRMED."""
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드")
    co = await _add_buyer(client, txn_id, company_name="코인")

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co["id"]},
    )
    mapping_id = create_resp.json()["id"]

    # TAPPING → CONFIRMED (유효)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"status": "CONFIRMED"},
    )
    assert resp.status_code == 200

    # CONFIRMED → TAPPING (무효)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"status": "TAPPING"},
    )
    assert resp.status_code == 422
    assert "상태 전이 불가" in resp.json()["detail"]


async def test_dropped_is_terminal(client) -> None:
    """DROPPED 상태에서는 어떤 전이도 불가."""
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드")
    co = await _add_buyer(client, txn_id, company_name="코인")

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co["id"]},
    )
    mapping_id = create_resp.json()["id"]

    # TAPPING → DROPPED
    await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"status": "DROPPED"},
    )

    # DROPPED → CONFIRMED (무효)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"status": "CONFIRMED"},
    )
    assert resp.status_code == 422

    # DROPPED → TAPPING (무효)
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"status": "TAPPING"},
    )
    assert resp.status_code == 422


async def test_equity_share_pct_boundary(client) -> None:
    """equity_share_pct 경계값 검증 — 0, 100 허용."""
    txn_id = await _create_txn(client)
    lead = await _add_buyer(client, txn_id, company_name="리드")
    co = await _add_buyer(client, txn_id, company_name="코인")

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/consortium/",
        json={"lead_buyer_id": lead["id"], "co_investor_buyer_id": co["id"]},
    )
    mapping_id = create_resp.json()["id"]

    # 0% — 유효
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"equity_share_pct": 0},
    )
    assert resp.status_code == 200
    assert resp.json()["equity_share_pct"] == "0.00"

    # 100% — 유효
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/consortium/{mapping_id}",
        json={"equity_share_pct": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["equity_share_pct"] == "100.00"


async def test_create_log_stores_email(client) -> None:
    txn_id = await _create_txn(client)
    buyer = await _add_buyer(client, txn_id)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
        json={
            "stage": "IDENTIFIED",
            "log_date": "2026-02-28",
            "content": "초기 접촉",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created_by_email"] == "test@example.com"
