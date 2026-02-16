"""보안 테스트 전용 Fixture — 역할별 사용자 + 딜 격리.

FDD-1705 (권한 우회) + FDD-1405 (민감정보 누출) 전용.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.token import create_access_token
from app.database import get_db
from app.main import app
from app.models.user import UserRole


def _make_user(role: UserRole, email: str | None = None) -> CurrentUser:
    """역할별 테스트 사용자 생성."""
    user_id = uuid.uuid4()
    email = email or f"{role.value.lower()}_{user_id.hex[:6]}@autofdd.dev"
    return CurrentUser(
        id=user_id,
        email=email,
        role=role,
        display_name=f"Test {role.value}",
    )


@pytest.fixture
def admin_user_obj() -> CurrentUser:
    return _make_user(UserRole.ADMIN)


@pytest.fixture
def analyst_user_obj() -> CurrentUser:
    return _make_user(UserRole.ANALYST)


@pytest.fixture
def viewer_user_obj() -> CurrentUser:
    return _make_user(UserRole.VIEWER)


@pytest.fixture
def reviewer_user_obj() -> CurrentUser:
    return _make_user(UserRole.REVIEWER)


def _make_token(user: CurrentUser) -> str:
    """JWT access token 생성."""
    return create_access_token(user.id, user.email, user.role.value)


@pytest.fixture
def admin_token(admin_user_obj) -> str:
    return _make_token(admin_user_obj)


@pytest.fixture
def analyst_token(analyst_user_obj) -> str:
    return _make_token(analyst_user_obj)


@pytest.fixture
def viewer_token(viewer_user_obj) -> str:
    return _make_token(viewer_user_obj)


@pytest.fixture
def reviewer_token(reviewer_user_obj) -> str:
    return _make_token(reviewer_user_obj)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict[str, str]:
    return _auth_header(admin_token)


@pytest.fixture
def analyst_headers(analyst_token) -> dict[str, str]:
    return _auth_header(analyst_token)


@pytest.fixture
def viewer_headers(viewer_token) -> dict[str, str]:
    return _auth_header(viewer_token)


@pytest.fixture
def reviewer_headers(reviewer_token) -> dict[str, str]:
    return _auth_header(reviewer_token)


@pytest.fixture
def sec_client(db: Session) -> Generator[TestClient, None, None]:
    """보안 테스트 전용 TestClient — DB override 포함."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def deal_by_admin(sec_client: TestClient, admin_user_obj: CurrentUser):
    """Admin이 생성한 딜 — 다른 역할의 접근 테스트에 사용."""
    app.dependency_overrides[get_current_user] = lambda: admin_user_obj
    try:
        resp = sec_client.post(
            "/api/v1/deals",
            json={
                "name": "Security Test Deal",
                "deal_type": "COMPLETION_ACCOUNTS",
                "reference_date": "2025-12-31",
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
            },
        )
        assert resp.status_code in (200, 201)
        return resp.json()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
