"""Golden path tests for the simplified workflow."""

import pytest
from httpx import AsyncClient

FULL_TXN = {
    "name": "Golden Path Workflow",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "Target Co",
    "client_name": "Client Co",
    "lead_advisor_email": "advisor@example.com",
}

PHASES = [
    "PREPARATION",
    "MARKETING",
    "BIDDING",
    "MAIN_DUE_DILIGENCE",
    "NEGOTIATION",
    "CLOSING",
    "POST_CLOSING",
]


async def _create_active_txn(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/transactions", json=FULL_TXN)
    assert resp.status_code == 201
    txn_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        json={"to_status": "ACTIVE"},
    )
    assert resp.status_code == 200
    return txn_id


async def _get_phase_status(client: AsyncClient, txn_id: str) -> dict:
    resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
    assert resp.status_code == 200
    return resp.json()


async def _advance(client: AsyncClient, txn_id: str, to_phase: str) -> dict:
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        json={"to_phase": to_phase},
    )
    return {"status_code": resp.status_code, "body": resp.json()}


@pytest.mark.asyncio
async def test_golden_path_full_lifecycle(client: AsyncClient):
    txn_id = await _create_active_txn(client)

    for phase in PHASES:
        status = await _get_phase_status(client, txn_id)
        assert status["prerequisites"] == []
        assert status["all_met"] is True
        assert status["pending_acknowledgements"] == []
        assert status["requires_user_acknowledgement"] is False

        result = await _advance(client, txn_id, phase)
        assert result["status_code"] == 200
        assert result["body"]["phase"] == phase

    status = await _get_phase_status(client, txn_id)
    assert status["current_phase"] == "POST_CLOSING"
    assert status["next_phase"] is None
    assert status["can_advance"] is False


@pytest.mark.asyncio
async def test_rollback_and_readvance_without_seed_data(client: AsyncClient):
    txn_id = await _create_active_txn(client)

    for phase in ["PREPARATION", "MARKETING", "BIDDING"]:
        result = await _advance(client, txn_id, phase)
        assert result["status_code"] == 200

    result = await _advance(client, txn_id, "MARKETING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "MARKETING"

    result = await _advance(client, txn_id, "BIDDING")
    assert result["status_code"] == 200
    assert result["body"]["phase"] == "BIDDING"


@pytest.mark.asyncio
async def test_phase_status_stays_empty_midstream(client: AsyncClient):
    txn_id = await _create_active_txn(client)

    for phase in ["PREPARATION", "MARKETING", "BIDDING", "MAIN_DUE_DILIGENCE"]:
        result = await _advance(client, txn_id, phase)
        assert result["status_code"] == 200

    status = await _get_phase_status(client, txn_id)
    assert status["current_phase"] == "MAIN_DUE_DILIGENCE"
    assert status["prerequisites"] == []
    assert status["gate_summary"] is None
    assert status["pending_acknowledgements"] == []
