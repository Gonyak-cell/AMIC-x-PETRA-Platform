"""Bid (IOI/LOI/Final Offer) API tests."""

import io

import pytest
from httpx import AsyncClient

from app.ralph.parsers.base import ParsedFile

pytestmark = pytest.mark.anyio

BASE = "/api/v1/transactions"

SAMPLE_TXN = {
    "name": "Bid Test Deal",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "Project Next",
    "client_name": "Amic Client",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_BUYER = {"company_name": "Samsung C&T", "buyer_type": "STRATEGIC"}


async def _setup(client: AsyncClient) -> tuple[str, str]:
    txn = await client.post(f"{BASE}", json=SAMPLE_TXN)
    txn_id = txn.json()["id"]
    buyer = await client.post(f"{BASE}/{txn_id}/buyers", json=SAMPLE_BUYER)
    return txn_id, buyer.json()["id"]


async def _upload_bid_attachment(
    client: AsyncClient,
    txn_id: str,
    *,
    filename: str = "SamsungC&T_LOI.pdf",
    content: bytes = b"%PDF-1.4 fake loi",
) -> dict:
    response = await client.post(
        f"{BASE}/{txn_id}/attachments",
        data={"entity_type": "BID"},
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


async def test_create_ioi(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    response = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_id,
            "bid_type": "IOI",
            "amount": 50000000000,
            "valuation_method": "EV_EBITDA",
            "multiple": 8.5,
            "submitted_at": "2026-03-15",
            "valid_until": "2026-04-15",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bid_type"] == "IOI"
    assert data["amount"] == 50000000000
    assert data["valuation_method"] == "EV_EBITDA"
    assert data["multiple"] == 8.5
    assert data["status"] == "SUBMITTED"


async def test_create_bid_syncs_buyer_snapshot(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    response = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_id,
            "bid_type": "IOI",
            "amount": 50000000000,
            "submitted_at": "2026-03-15",
        },
    )
    assert response.status_code == 201

    buyer_response = await client.get(f"{BASE}/{txn_id}/buyers/{buyer_id}")
    assert buyer_response.status_code == 200
    buyer = buyer_response.json()
    assert buyer["ioi_value"] == "50000000000.00"
    assert buyer["ioi_date"] == "2026-03-15"


async def test_create_loi(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    response = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={
            "buyer_candidate_id": buyer_id,
            "bid_type": "LOI",
            "amount": 55000000000,
            "conditions": "DD results subject to confirmatory review",
        },
    )
    assert response.status_code == 201
    assert response.json()["bid_type"] == "LOI"


async def test_list_bids(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI", "amount": 50000000000},
    )
    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI", "amount": 55000000000},
    )

    response = await client.get(f"{BASE}/{txn_id}/bids")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_bids_filter_type(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI"},
    )
    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI"},
    )

    response = await client.get(f"{BASE}/{txn_id}/bids", params={"type": "IOI"})
    assert len(response.json()) == 1
    assert response.json()[0]["bid_type"] == "IOI"


async def test_update_bid_status(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    create_response = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI", "amount": 50000000000},
    )
    bid_id = create_response.json()["id"]

    response = await client.patch(
        f"{BASE}/{txn_id}/bids/{bid_id}",
        json={"status": "ACCEPTED"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"


async def test_update_bid_amount(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    create_response = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI", "amount": 50000000000},
    )
    bid_id = create_response.json()["id"]

    response = await client.patch(
        f"{BASE}/{txn_id}/bids/{bid_id}",
        json={"amount": 52000000000, "notes": "Updated after management meeting"},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 52000000000


async def test_update_bid_404(client: AsyncClient):
    txn_id, _ = await _setup(client)
    fake_bid = "00000000-0000-0000-0000-000000000000"
    response = await client.patch(
        f"{BASE}/{txn_id}/bids/{fake_bid}",
        json={"status": "ACCEPTED"},
    )
    assert response.status_code == 404


async def test_delete_bid(client: AsyncClient):
    txn_id, buyer_id = await _setup(client)
    create_response = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "IOI"},
    )
    bid_id = create_response.json()["id"]

    response = await client.delete(f"{BASE}/{txn_id}/bids/{bid_id}")
    assert response.status_code == 204


async def test_bid_comparison_matrix(client: AsyncClient):
    txn_id, buyer1_id = await _setup(client)
    buyer2 = await client.post(
        f"{BASE}/{txn_id}/buyers",
        json={"company_name": "MBK Partners", "buyer_type": "FINANCIAL_SPONSOR"},
    )
    buyer2_id = buyer2.json()["id"]

    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer1_id, "bid_type": "IOI", "amount": 50000000000},
    )
    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer1_id, "bid_type": "LOI", "amount": 55000000000},
    )
    await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer2_id, "bid_type": "IOI", "amount": 48000000000},
    )

    response = await client.get(f"{BASE}/{txn_id}/bids/comparison")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    samsung = next(item for item in data if item["buyer_name"] == "Samsung C&T")
    assert samsung["ioi"] is not None
    assert samsung["ioi"]["amount"] == 50000000000
    assert samsung["loi"] is not None
    assert samsung["loi"]["amount"] == 55000000000
    assert samsung["final_offer"] is None

    mbk = next(item for item in data if item["buyer_name"] == "MBK Partners")
    assert mbk["ioi"] is not None
    assert mbk["loi"] is None


async def test_import_bid_from_attachment_creates_bid_and_syncs_buyer(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    txn_id, buyer_id = await _setup(client)
    attachment = await _upload_bid_attachment(client, txn_id)

    def fake_parse_file(path: str) -> ParsedFile:
        return ParsedFile(
            source_path=path,
            file_type="pdf",
            text="\n".join(
                [
                    "Samsung C&T Letter of Intent",
                    "Offer Price: KRW 55,000,000,000",
                    "Submitted on 2026-03-20",
                    "Valid until 2026-04-05",
                    "EV/EBITDA 8.5x",
                ]
            ),
        )

    monkeypatch.setattr("app.services.bid_import_service.parse_file", fake_parse_file)

    response = await client.post(
        f"{BASE}/{txn_id}/bids/import-from-attachment",
        json={"attachment_id": attachment["id"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["buyer_name"] == "Samsung C&T"
    assert body["bid"]["bid_type"] == "LOI"
    assert body["bid"]["amount"] == 55000000000
    assert body["bid"]["submitted_at"] == "2026-03-20"
    assert body["bid"]["valid_until"] == "2026-04-05"
    assert body["bid"]["valuation_method"] == "EV_EBITDA"
    assert body["bid"]["multiple"] == 8.5

    attachments_response = await client.get(
        f"{BASE}/{txn_id}/attachments",
        params={"entity_type": "BID"},
    )
    assert attachments_response.status_code == 200
    uploaded = attachments_response.json()["items"][0]
    assert uploaded["entity_id"] == body["bid"]["id"]

    buyer_response = await client.get(f"{BASE}/{txn_id}/buyers/{buyer_id}")
    buyer = buyer_response.json()
    assert buyer["loi_value"] == "55000000000.00"
    assert buyer["loi_date"] == "2026-03-20"


async def test_import_bid_from_attachment_updates_incomplete_existing_bid(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    txn_id, buyer_id = await _setup(client)
    existing = await client.post(
        f"{BASE}/{txn_id}/bids",
        json={"buyer_candidate_id": buyer_id, "bid_type": "LOI"},
    )
    attachment = await _upload_bid_attachment(client, txn_id, filename="SamsungC&T_LOI_v2.pdf")

    def fake_parse_file(path: str) -> ParsedFile:
        return ParsedFile(
            source_path=path,
            file_type="pdf",
            text="\n".join(
                [
                    "Samsung C&T LOI",
                    "Purchase Price KRW 57,000,000,000",
                    "2026-03-25",
                ]
            ),
        )

    monkeypatch.setattr("app.services.bid_import_service.parse_file", fake_parse_file)

    response = await client.post(
        f"{BASE}/{txn_id}/bids/import-from-attachment",
        json={
            "attachment_id": attachment["id"],
            "buyer_candidate_id": buyer_id,
            "bid_type": "LOI",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is False
    assert body["bid"]["id"] == existing.json()["id"]
    assert body["bid"]["amount"] == 57000000000
    assert body["bid"]["submitted_at"] == "2026-03-25"
