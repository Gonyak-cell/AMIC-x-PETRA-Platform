"""Workflow tests for the hurdle-free phase progression model."""

from httpx import AsyncClient

FULL_TXN = {
    "name": "Phase Flow Test",
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


async def _advance_to(client: AsyncClient, txn_id: str, target_phase: str) -> None:
    current_index = PHASES.index(target_phase)
    for phase in PHASES[: current_index + 1]:
        resp = await client.post(
            f"/api/v1/transactions/{txn_id}/workflow/advance",
            json={"to_phase": phase},
        )
        assert resp.status_code == 200, resp.text


class TestHurdleFreeWorkflow:
    async def test_phase_status_has_no_prerequisites(self, client: AsyncClient):
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "MARKETING")

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["prerequisites"] == []
        assert data["all_met"] is True
        assert data["can_advance"] is True
        assert data["gate_summary"] is None
        assert data["pending_acknowledgements"] == []
        assert data["requires_user_acknowledgement"] is False

    async def test_can_advance_without_seed_data_or_acks(self, client: AsyncClient):
        txn_id = await _create_active_txn(client)

        for phase in PHASES:
            resp = await client.post(
                f"/api/v1/transactions/{txn_id}/workflow/advance",
                json={"to_phase": phase},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["phase"] == phase

    async def test_draft_transaction_cannot_advance(self, client: AsyncClient):
        resp = await client.post("/api/v1/transactions", json=FULL_TXN)
        assert resp.status_code == 201
        txn_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["can_advance"] is False
        assert data["blocking_reasons"]

    async def test_last_phase_has_no_next_phase(self, client: AsyncClient):
        txn_id = await _create_active_txn(client)
        await _advance_to(client, txn_id, "POST_CLOSING")

        resp = await client.get(f"/api/v1/transactions/{txn_id}/workflow/phase-status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["current_phase"] == "POST_CLOSING"
        assert data["next_phase"] is None
        assert data["can_advance"] is False
        assert data["blocking_reasons"]
