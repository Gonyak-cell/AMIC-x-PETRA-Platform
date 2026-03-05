"""미팅 로그 API 테스트."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# ── 헬퍼 ──────────────────────────────────────────────────


async def _create_meeting(client: AsyncClient, txn_id: str, **overrides) -> dict:
    payload = {
        "meeting_phase": "MARKETING",
        "title": "잠재 매수인 A사 미팅",
        "meeting_date": "2026-03-01",
        "meeting_time": "14:00",
        "location": "서울 강남",
        "channel": "IN_PERSON",
        "status": "COMPLETED",
        "minutes": "A사와 매각 조건 논의. 관심 표명.",
        "summary": "A사 관심 높음",
        "provided_materials": [{"name": "티저메모", "description": "비밀유지 전 요약본"}],
        "attendees": [
            {"name": "김어드바이저", "email": "kim@example.com", "role": "SELLER_ADVISOR"},
            {
                "name": "이매수인",
                "deal_type": "MA",
                "email": "lee@buyer.com",
                "organization": "A사",
                "role": "COUNTERPARTY",
                "reaction": "POSITIVE",
                "comments": "밸류 적정 수준",
            },
        ],
        **overrides,
    }
    resp = await client.post(f"/api/v1/transactions/{txn_id}/meeting-logs", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── 미팅 로그 CRUD ────────────────────────────────────────


async def test_create_marketing_meeting(client: AsyncClient, transaction_id: str):
    data = await _create_meeting(client, transaction_id)
    assert data["meeting_phase"] == "MARKETING"
    assert data["title"] == "잠재 매수인 A사 미팅"
    assert data["channel"] == "IN_PERSON"
    assert data["attendee_count"] == 2


async def test_create_negotiation_meeting(client: AsyncClient, transaction_id: str):
    data = await _create_meeting(
        client,
        transaction_id,
        meeting_phase="NEGOTIATION",
        title="SPA 초안 협상",
        channel="VIDEO",
        attendees=[{"name": "박변호사", "role": "LEGAL_COUNSEL"}],
    )
    assert data["meeting_phase"] == "NEGOTIATION"
    assert data["channel"] == "VIDEO"
    assert data["attendee_count"] == 1


async def test_list_meetings_filter_phase(client: AsyncClient, transaction_id: str):
    await _create_meeting(client, transaction_id, meeting_phase="MARKETING", title="마케팅 미팅")
    await _create_meeting(client, transaction_id, meeting_phase="NEGOTIATION", title="협상 미팅")

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs?meeting_phase=MARKETING")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["meeting_phase"] == "MARKETING"


async def test_get_meeting_detail(client: AsyncClient, transaction_id: str):
    created = await _create_meeting(client, transaction_id)
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs/{created['id']}")
    assert resp.status_code == 200
    detail = resp.json()
    assert len(detail["attendees"]) == 2
    assert detail["attendees"][1]["reaction"] == "POSITIVE"


async def test_update_meeting(client: AsyncClient, transaction_id: str):
    created = await _create_meeting(client, transaction_id)
    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{created['id']}",
        json={"status": "CANCELLED", "summary": "미팅 취소됨"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


async def test_delete_meeting(client: AsyncClient, transaction_id: str):
    created = await _create_meeting(client, transaction_id)
    resp = await client.delete(f"/api/v1/transactions/{transaction_id}/meeting-logs/{created['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs")
    assert resp.json()["total"] == 0


async def test_meeting_summary(client: AsyncClient, transaction_id: str):
    await _create_meeting(client, transaction_id, channel="IN_PERSON")
    await _create_meeting(client, transaction_id, channel="EMAIL", title="이메일 미팅")
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs/summary?meeting_phase=MARKETING")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total"] == 2


# ── 참석자 CRUD ──────────────────────────────────────────


async def test_add_attendee(client: AsyncClient, transaction_id: str):
    meeting = await _create_meeting(client, transaction_id)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}/attendees",
        json={"name": "최신입", "role": "OBSERVER"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "최신입"


async def test_update_attendee_reaction(client: AsyncClient, transaction_id: str):
    meeting = await _create_meeting(client, transaction_id)
    detail = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}")
    att_id = detail.json()["attendees"][1]["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}/attendees/{att_id}",
        json={"reaction": "VERY_POSITIVE", "comments": "매우 긍정적 반응으로 변경"},
    )
    assert resp.status_code == 200
    assert resp.json()["reaction"] == "VERY_POSITIVE"


async def test_remove_attendee(client: AsyncClient, transaction_id: str):
    meeting = await _create_meeting(client, transaction_id)
    detail = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}")
    att_id = detail.json()["attendees"][0]["id"]

    resp = await client.delete(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}/attendees/{att_id}",
    )
    assert resp.status_code == 204


# ── 액션아이템 CRUD ──────────────────────────────────────


async def test_create_action_item(client: AsyncClient, transaction_id: str):
    meeting = await _create_meeting(client, transaction_id)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}/action-items",
        json={"title": "NDA 초안 발송", "assignee_name": "김어드바이저", "due_date": "2026-03-05", "priority": "HIGH"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "NDA 초안 발송"
    assert resp.json()["status"] == "PENDING"


async def test_update_action_item_status(client: AsyncClient, transaction_id: str):
    meeting = await _create_meeting(client, transaction_id)
    item_resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}/action-items",
        json={"title": "추가 자료 요청"},
    )
    item_id = item_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}/meeting-logs/{meeting['id']}/action-items/{item_id}",
        json={"status": "COMPLETED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"


async def test_404_nonexistent_meeting(client: AsyncClient, transaction_id: str):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/meeting-logs/{fake_id}")
    assert resp.status_code == 404


async def test_condition_match(client: AsyncClient, transaction_id: str):
    data = await _create_meeting(
        client,
        transaction_id,
        condition_match="PARTIAL_MATCH",
        condition_notes="가격 조건은 일치하나 시기 불일치",
    )
    assert data["condition_match"] == "PARTIAL_MATCH"
    assert "가격 조건" in data["condition_notes"]
