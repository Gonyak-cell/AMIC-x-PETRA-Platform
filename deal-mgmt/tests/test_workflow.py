"""7단계 워크플로우 상태 머신 API 테스트."""

# 전제 조건을 모두 충족하는 거래 데이터
FULL_TXN = {
    "name": "워크플로우 테스트",
    "code_name": "WF-001",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
    "deal_captain_email": "captain@example.com",
    "industry": "Tech",
    "deal_structure": "100% 지분 인수",
    "estimated_deal_value": 1000000000,
}


async def _create_active_txn(client, code_name: str = "WF-001") -> str:
    """ACTIVE 상태의 거래를 생성하는 헬퍼."""
    txn = {**FULL_TXN, "code_name": code_name}
    resp = await client.post("/api/v1/transactions", json=txn)
    txn_id = resp.json()["id"]
    # DRAFT → ACTIVE
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    return txn_id


# ── Phase Status ───────────────────────────────────────────
async def test_phase_status_initial(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_phase"] == "ENGAGEMENT"
    assert data["next_phase"] == "PREPARATION"
    assert data["previous_phase"] is None


# ── Status Change ──────────────────────────────────────────
async def test_status_draft_to_active(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


async def test_status_draft_to_terminated(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "TERMINATED", "reason": "딜 취소"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "TERMINATED"


async def test_status_invalid_transition(client):
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    txn_id = resp.json()["id"]

    # DRAFT → COMPLETED (불가)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "COMPLETED"},
    )
    assert resp.status_code == 422


async def test_status_active_to_on_hold(client):
    txn_id = await _create_active_txn(client)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ON_HOLD", "reason": "고객 요청"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ON_HOLD"


async def test_status_on_hold_to_active(client):
    txn_id = await _create_active_txn(client, code_name="WF-HOLD")

    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ON_HOLD"},
    )
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


async def test_status_completed_is_terminal(client):
    txn_id = await _create_active_txn(client, code_name="WF-COMP")

    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "COMPLETED"},
    )
    # COMPLETED → ACTIVE (불가)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 422


# ── Phase Advance ──────────────────────────────────────────
async def test_advance_engagement_to_preparation(client):
    txn_id = await _create_active_txn(client, code_name="WF-ADV1")

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    assert resp.status_code == 200
    assert resp.json()["phase"] == "PREPARATION"


async def test_advance_skip_phase_fails(client):
    txn_id = await _create_active_txn(client, code_name="WF-SKIP")

    # ENGAGEMENT → MARKETING (2단계 건너뛰기 — 불가)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "MARKETING"},
    )
    assert resp.status_code == 422


async def test_advance_requires_active_status(client):
    resp = await client.post("/api/v1/transactions", json={**FULL_TXN, "code_name": "WF-DRAFT"})
    txn_id = resp.json()["id"]

    # DRAFT 상태에서 advance 시도
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    assert resp.status_code == 422


# ── Phase Rollback ─────────────────────────────────────────
async def test_rollback_phase(client):
    txn_id = await _create_active_txn(client, code_name="WF-ROLL")

    # ENGAGEMENT → PREPARATION
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    # PREPARATION → ENGAGEMENT (롤백)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "ENGAGEMENT"},
    )
    assert resp.status_code == 200
    assert resp.json()["phase"] == "ENGAGEMENT"


# ── Multi-phase Advance ───────────────────────────────────
async def test_advance_through_multiple_phases(client):
    txn_id = await _create_active_txn(client, code_name="WF-MULTI")

    phases = ["PREPARATION", "MARKETING", "BIDDING_DD", "NEGOTIATION"]
    for phase in phases:
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": phase},
        )
        assert resp.status_code == 200
        assert resp.json()["phase"] == phase


async def test_advance_missing_prerequisites(client):
    """전제 조건 미충족 시 전진 불가."""
    # industry 없는 거래 생성 (MARKETING 전제 조건)
    minimal_txn = {
        "name": "미완성 거래",
        "code_name": "WF-PREREQ",
        "side": "SELL",
        "target_company_name": "대상기업",
        "client_name": "의뢰기업",
        "lead_advisor_email": "advisor@example.com",
    }
    resp = await client.post("/api/v1/transactions", json=minimal_txn)
    txn_id = resp.json()["id"]

    # DRAFT → ACTIVE
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    # ENGAGEMENT → PREPARATION (OK: client_name + lead_advisor 있음)
    await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "PREPARATION"},
    )
    # PREPARATION → MARKETING (FAIL: industry 없음)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": "MARKETING"},
    )
    assert resp.status_code == 422
