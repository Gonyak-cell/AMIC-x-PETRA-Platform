"""CLIENT 초대 시스템 테스트 — TDD."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invite_token import InviteStatus, InviteToken
from app.models.user import User, UserRole

# ──────────────────────────────────────────────
# 헬퍼 상수
# ──────────────────────────────────────────────
_INVITE_URL = "/api/v1/auth/invite"
_VERIFY_URL = "/api/v1/auth/invite/verify"
_ACCEPT_URL = "/api/v1/auth/invite/accept"

_DEAL_IDS = [str(uuid.uuid4())]
_DEAL_NAMES = ["테스트 거래 A"]


def _invite_payload(email: str = "client@test.com") -> dict:
    return {
        "email": email,
        "display_name": "테스트 클라이언트",
        "title": "대표이사",
        "transaction_ids": _DEAL_IDS,
        "transaction_names": _DEAL_NAMES,
    }


# ──────────────────────────────────────────────
# TASK 1 — 신규 CLIENT 초대 성공
# ──────────────────────────────────────────────
@pytest.mark.db
def test_create_invite_success_new_user(client: TestClient, db: Session) -> None:
    """신규 CLIENT 초대 시 사용자가 생성되고 토큰이 PENDING 상태여야 한다."""
    with patch("app.services.invite_service.send_invite_email") as mock_send:
        resp = client.post(_INVITE_URL, json=_invite_payload())

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_new_user"] is True
    assert body["assigned_deal_count"] == 1
    assert body["invite_sent"] is True
    assert body["invite_error"] is None

    # DB 검증 — 사용자가 CLIENT, is_active=False
    user = db.scalar(select(User).where(User.email == "client@test.com"))
    assert user is not None
    assert user.role == UserRole.CLIENT
    assert user.is_active is False

    # DB 검증 — 토큰이 PENDING
    invite = db.scalar(select(InviteToken).where(InviteToken.user_id == user.id))
    assert invite is not None
    assert invite.status == InviteStatus.PENDING

    mock_send.assert_called_once()


# ──────────────────────────────────────────────
# TASK 2 — 내부 사용자(ADMIN 등) 초대 차단
# ──────────────────────────────────────────────
@pytest.mark.db
def test_create_invite_blocks_non_client_user(client: TestClient, db: Session) -> None:
    """이미 존재하는 ADMIN 계정 이메일로 초대 시 에러를 반환해야 한다."""
    from app.auth.password import hash_password

    admin = User(
        email="admin_existing@test.com",
        hashed_password=hash_password("adminpass"),
        display_name="기존 어드민",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    resp = client.post(_INVITE_URL, json=_invite_payload("admin_existing@test.com"))
    # FDDError → 401 (AuthenticationError)
    assert resp.status_code == 401, resp.text


# ──────────────────────────────────────────────
# TASK 3 — 유효하지 않은 토큰 검증
# ──────────────────────────────────────────────
@pytest.mark.db
def test_verify_invalid_token(client: TestClient) -> None:
    """존재하지 않는 토큰 검증 시 valid=False여야 한다."""
    resp = client.post(_VERIFY_URL, json={"token": "nonexistent-token-xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False


# ──────────────────────────────────────────────
# TASK 4 — 전체 초대 플로우: create → verify → accept
# ──────────────────────────────────────────────
@pytest.mark.db
def test_full_invite_flow(client: TestClient, db: Session) -> None:
    """초대 생성 → 토큰 검증 → 초대 수락의 전체 흐름을 테스트한다."""
    # 1) 초대 생성
    with patch("app.services.invite_service.send_invite_email"):
        resp = client.post(_INVITE_URL, json=_invite_payload("newclient@flow.com"))
    assert resp.status_code == 201, resp.text

    # 발급된 토큰 조회
    user = db.scalar(select(User).where(User.email == "newclient@flow.com"))
    assert user is not None
    invite = db.scalar(select(InviteToken).where(InviteToken.user_id == user.id))
    assert invite is not None
    raw_token = invite.token

    # 2) 토큰 검증
    verify_resp = client.post(_VERIFY_URL, json={"token": raw_token})
    assert verify_resp.status_code == 200
    verify_body = verify_resp.json()
    assert verify_body["valid"] is True
    assert verify_body["email"] == "newclient@flow.com"

    # 3) 초대 수락 + 비밀번호 설정
    accept_resp = client.post(
        _ACCEPT_URL,
        json={"token": raw_token, "password": "newpassword123"},
    )
    assert accept_resp.status_code == 200, accept_resp.text
    accept_body = accept_resp.json()
    assert accept_body["email"] == "newclient@flow.com"

    # DB 검증 — is_active=True, 토큰 ACCEPTED
    db.refresh(user)
    db.refresh(invite)
    assert user.is_active is True
    assert invite.status == InviteStatus.ACCEPTED
    assert invite.accepted_at is not None


# ──────────────────────────────────────────────
# 추가: 이미 활성화된 CLIENT 재초대 시 조기 반환
# ──────────────────────────────────────────────
@pytest.mark.db
def test_create_invite_active_client_returns_early(
    client: TestClient, db: Session
) -> None:
    """이미 활성화된 CLIENT 재초대 시 invite_sent=False를 반환해야 한다."""
    from app.auth.password import hash_password

    active_client = User(
        email="active_client@test.com",
        hashed_password=hash_password("somepass"),
        display_name="활성 클라이언트",
        role=UserRole.CLIENT,
        is_active=True,
    )
    db.add(active_client)
    db.commit()

    resp = client.post(_INVITE_URL, json=_invite_payload("active_client@test.com"))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["invite_sent"] is False
    assert body["invite_error"] == "이미 활성화된 CLIENT"


# ──────────────────────────────────────────────
# 추가: 수락 후 토큰 재사용 차단
# ──────────────────────────────────────────────
@pytest.mark.db
def test_accept_invite_token_already_used(client: TestClient, db: Session) -> None:
    """이미 수락된 토큰으로 accept 요청 시 에러를 반환해야 한다."""
    with patch("app.services.invite_service.send_invite_email"):
        resp = client.post(_INVITE_URL, json=_invite_payload("reuse@test.com"))
    assert resp.status_code == 201

    user = db.scalar(select(User).where(User.email == "reuse@test.com"))
    assert user is not None
    invite = db.scalar(select(InviteToken).where(InviteToken.user_id == user.id))
    assert invite is not None
    raw_token = invite.token

    # 첫 수락
    r1 = client.post(_ACCEPT_URL, json={"token": raw_token, "password": "pass1234"})
    assert r1.status_code == 200

    # 두 번째 수락 시도
    r2 = client.post(_ACCEPT_URL, json={"token": raw_token, "password": "pass1234"})
    assert r2.status_code == 401, r2.text
