"""Engagement and Working Group API tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from app.core.security import JWTClaims, get_jwt_claims
from app.main import app

SAMPLE_TXN = {
    "name": "프로젝트 감마",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "감마기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}

SAMPLE_ENGAGEMENT = {
    "type": "EXCLUSIVE",
    "fee_structure": {"retainer": 50000, "success_pct": 2.0},
    "signed_at": "2026-01-15",
    "expires_at": "2027-01-15",
    "notes": "독점 자문 계약",
}

SAMPLE_MEMBER = {
    "name": "김변호사",
    "email": "kim@lawfirm.co.kr",
    "organization": "김앤장 법률사무소",
    "role": "LEGAL_COUNSEL",
    "phone": "02-1234-5678",
}


def _member_payload(**overrides) -> dict[str, str]:
    return {**SAMPLE_MEMBER, **overrides}


def _claims(
    *,
    role: str,
    email: str,
    display_name: str | None = None,
    user_id: str = "test-user-id",
) -> JWTClaims:
    return JWTClaims(
        user_id=user_id,
        email=email,
        role=role,
        display_name=display_name,
    )


@pytest.fixture
async def override_claims() -> AsyncGenerator:
    previous = app.dependency_overrides.get(get_jwt_claims)

    def _set(claims: JWTClaims) -> None:
        async def _override() -> JWTClaims:
            return claims

        app.dependency_overrides[get_jwt_claims] = _override

    yield _set

    if previous is not None:
        app.dependency_overrides[get_jwt_claims] = previous
    else:
        app.dependency_overrides.pop(get_jwt_claims, None)


async def _create_txn(client, **overrides) -> str:
    body = {**SAMPLE_TXN, **overrides}
    resp = await client.post("/api/v1/transactions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_engagement(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json=SAMPLE_ENGAGEMENT,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "EXCLUSIVE"
    assert data["fee_structure"]["success_pct"] == 2.0
    assert data["signed_at"] == "2026-01-15"
    assert data["transaction_id"] == txn_id


async def test_list_engagements(client):
    txn_id = await _create_txn(client)
    await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json=SAMPLE_ENGAGEMENT,
    )
    await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json={**SAMPLE_ENGAGEMENT, "type": "CO_ADVISORY"},
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/engagements")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_engagement(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json=SAMPLE_ENGAGEMENT,
    )
    eng_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/engagements/{eng_id}",
        json={"type": "NON_EXCLUSIVE", "notes": "비독점으로 변경"},
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "NON_EXCLUSIVE"
    assert resp.json()["notes"] == "비독점으로 변경"


async def test_delete_engagement(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/engagements",
        json=SAMPLE_ENGAGEMENT,
    )
    eng_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/engagements/{eng_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/engagements")
    assert len(list_resp.json()) == 0


async def test_engagement_404_invalid_txn(client):
    fake_txn = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/transactions/{fake_txn}/engagements",
        json=SAMPLE_ENGAGEMENT,
    )
    assert resp.status_code == 404


async def test_engagement_update_404(client):
    txn_id = await _create_txn(client)
    fake_eng = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/engagements/{fake_eng}",
        json={"notes": "없는 계약"},
    )
    assert resp.status_code == 404


async def test_add_member(client):
    txn_id = await _create_txn(client)
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=SAMPLE_MEMBER,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "김변호사"
    assert data["role"] == "LEGAL_COUNSEL"
    assert data["is_active"] is True


async def test_list_members(client):
    txn_id = await _create_txn(client)
    await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=_member_payload(
            name="박회계사",
            email="park@accounting.co.kr",
            role="ACCOUNTING_ADVISOR",
        ),
    )

    resp = await client.get(f"/api/v1/transactions/{txn_id}/members")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_member_as_manager(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=SAMPLE_MEMBER,
    )
    member_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{member_id}",
        json={"organization": "법무법인 세종", "role": "OTHER"},
    )
    assert resp.status_code == 200
    assert resp.json()["organization"] == "법무법인 세종"
    assert resp.json()["role"] == "OTHER"


async def test_remove_member_as_manager(client):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=SAMPLE_MEMBER,
    )
    member_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/members/{member_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/transactions/{txn_id}/members")
    assert len(list_resp.json()) == 0


async def test_duplicate_member_email(client):
    txn_id = await _create_txn(client)
    await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    resp = await client.post(f"/api/v1/transactions/{txn_id}/members", json=SAMPLE_MEMBER)
    assert resp.status_code == 409


async def test_member_404(client):
    txn_id = await _create_txn(client)
    fake_member = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{fake_member}",
        json={"name": "없는 멤버"},
    )
    assert resp.status_code == 404


async def test_analyst_cannot_add_member(client, override_claims):
    txn_id = await _create_txn(client)
    override_claims(
        _claims(
            role="ANALYST",
            email="analyst@example.com",
            display_name="이분석",
        )
    )

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=SAMPLE_MEMBER,
    )
    assert resp.status_code == 403


async def test_analyst_cannot_remove_member(client, override_claims):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=SAMPLE_MEMBER,
    )
    member_id = create_resp.json()["id"]

    override_claims(
        _claims(
            role="ANALYST",
            email="analyst@example.com",
            display_name="이분석",
        )
    )

    resp = await client.delete(f"/api/v1/transactions/{txn_id}/members/{member_id}")
    assert resp.status_code == 403


async def test_member_can_update_own_contact_details_by_name(client, override_claims):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=_member_payload(
            name="조우상",
            email="shared-team@amic.kr",
            organization="페트라브릿지파트너스",
        ),
    )
    member_id = create_resp.json()["id"]

    override_claims(
        _claims(
            role="ANALYST",
            email="different-email@amic.kr",
            display_name="조우상",
        )
    )

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{member_id}",
        json={"organization": "AMIC", "phone": "010-9999-0000"},
    )
    assert resp.status_code == 200
    assert resp.json()["organization"] == "AMIC"
    assert resp.json()["phone"] == "010-9999-0000"


async def test_member_cannot_update_other_member(client, override_claims):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=_member_payload(name="김양태", email="ytkim@amic.kr"),
    )
    member_id = create_resp.json()["id"]

    override_claims(
        _claims(
            role="ANALYST",
            email="someone-else@amic.kr",
            display_name="조우상",
        )
    )

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{member_id}",
        json={"organization": "무단수정"},
    )
    assert resp.status_code == 403


async def test_member_cannot_change_role_on_own_row(client, override_claims):
    txn_id = await _create_txn(client)
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/members",
        json=_member_payload(name="조우상", email="wsjo@amic.kr"),
    )
    member_id = create_resp.json()["id"]

    override_claims(
        _claims(
            role="ANALYST",
            email="wsjo@amic.kr",
            display_name="조우상",
        )
    )

    resp = await client.patch(
        f"/api/v1/transactions/{txn_id}/members/{member_id}",
        json={"role": "OTHER"},
    )
    assert resp.status_code == 403
