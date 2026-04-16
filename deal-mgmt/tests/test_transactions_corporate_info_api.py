from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio

SAMPLE_TXN = {
    "name": "Project Guided",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "Target Co",
    "client_name": "Client Co",
    "lead_advisor_email": "advisor@example.com",
}


async def test_patch_transaction_corporate_info_ignores_unknown_keys(client) -> None:
    create_resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert create_resp.status_code == 201
    txn_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}",
        json={
            "corporate_info": {
                "company_name": "Target Co",
                "representative_name": "홍길동",
                "unknown_field": "should-be-dropped",
            }
        },
    )

    assert resp.status_code == 200
    corporate_info = resp.json()["corporate_info"]
    assert corporate_info["company_name"] == "Target Co"
    assert corporate_info["representative_name"] == "홍길동"
    assert "unknown_field" not in corporate_info
