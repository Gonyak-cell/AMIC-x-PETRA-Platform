"""협상 이견 추적 API 테스트."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _create_meeting(client: AsyncClient, txn_id: str) -> dict:
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/meeting-logs",
        json={
            "meeting_phase": "NEGOTIATION",
            "title": "SPA 협상",
            "meeting_date": "2026-03-10",
            "channel": "IN_PERSON",
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_issue(client: AsyncClient, txn_id: str, **overrides) -> dict:
    payload = {
        "title": "가격 조정 조항",
        "clause_reference": "SPA 제4.2조",
        "category": "가격",
        "our_position": "확정 가격 방식. Closing일 기준 운전자본 조정만 허용.",
        "counterpart_position": "어닝아웃 10% 포함. 1년 성과 연동.",
        "legal_review": "운전자본 조정은 통상적. 어닝아웃은 분쟁 소지 있음.",
        "priority": "HIGH",
        **overrides,
    }
    resp = await client.post(f"/api/v1/transactions/{txn_id}/negotiation-issues", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def test_create_issue(client: AsyncClient, transaction_id: str):
    data = await _create_issue(client, transaction_id)
    assert data["title"] == "가격 조정 조항"
    assert data["status"] == "OPEN"
    assert data["priority"] == "HIGH"
    assert "확정 가격" in data["our_position"]
    assert "어닝아웃" in data["counterpart_position"]


async def test_create_issue_with_meeting(client: AsyncClient, transaction_id: str):
    meeting = await _create_meeting(client, transaction_id)
    data = await _create_issue(client, transaction_id, meeting_id=meeting["id"])
    assert data["meeting_id"] == meeting["id"]


async def test_list_issues_filter_status(client: AsyncClient, transaction_id: str):
    await _create_issue(client, transaction_id, title="이슈 1")
    issue2 = await _create_issue(client, transaction_id, title="이슈 2")
    await client.patch(
        f"/api/v1/transactions/{transaction_id}/negotiation-issues/{issue2['id']}",
        json={"status": "AGREED", "resolution": "어닝아웃 5%로 합의"},
    )

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/negotiation-issues?status=OPEN")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/negotiation-issues?status=AGREED")
    assert resp.json()["total"] == 1


async def test_update_issue(client: AsyncClient, transaction_id: str):
    issue = await _create_issue(client, transaction_id)
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/negotiation-issues/{issue['id']}",
        json={"status": "AGREED", "resolution": "양측 합의: 확정 가격 + 운전자본 조정"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "AGREED"
    assert "합의" in resp.json()["resolution"]


async def test_delete_issue(client: AsyncClient, transaction_id: str):
    issue = await _create_issue(client, transaction_id)
    resp = await client.delete(f"/api/v1/transactions/{transaction_id}/negotiation-issues/{issue['id']}")
    assert resp.status_code == 204


async def test_ai_suggest_clause(client: AsyncClient, transaction_id: str):
    issue = await _create_issue(client, transaction_id)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/negotiation-issues/{issue['id']}/ai-suggest",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_text" in data
    assert data["confidence"] == 0.0  # MVP stub


async def test_404_nonexistent_issue(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/negotiation-issues/{fake_id}")
    assert resp.status_code == 404
