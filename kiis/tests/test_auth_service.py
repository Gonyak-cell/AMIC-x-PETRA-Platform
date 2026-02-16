from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.schemas.auth import UserCreate
from app.services.auth_service import AuthService


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService()


@pytest.fixture
def sample_user_create() -> UserCreate:
    return UserCreate(
        username="testuser",
        email="test@example.com",
        password="securepass123",
    )


# --- TestPasswordHashing ---


class TestPasswordHashing:
    """비밀번호 해시 생성 및 검증 테스트"""

    async def test_hash_password(self) -> None:
        """비밀번호 해시가 원문과 다르게 생성된다."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt 해시 형식

    async def test_verify_password_correct(self) -> None:
        """올바른 비밀번호 검증이 성공한다."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    async def test_verify_password_wrong(self) -> None:
        """잘못된 비밀번호 검증이 실패한다."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False


# --- TestTokenCreation ---


class TestTokenCreation:
    """JWT 토큰 생성 테스트"""

    async def test_create_access_token(self) -> None:
        """액세스 토큰이 정상 생성되고 디코딩 가능하다."""
        data = {"sub": "testuser", "role": "viewer"}
        token = create_access_token(data=data)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["role"] == "viewer"
        assert "exp" in payload

    async def test_create_access_token_custom_expiry(self) -> None:
        """커스텀 만료 시간으로 액세스 토큰을 생성할 수 있다."""
        data = {"sub": "testuser", "role": "viewer"}
        token = create_access_token(data=data, expires_delta=timedelta(minutes=60))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "testuser"

    async def test_create_refresh_token(self) -> None:
        """리프레시 토큰이 정상 생성되고 type=refresh 클레임을 포함한다."""
        data = {"sub": "testuser", "role": "viewer"}
        token = create_refresh_token(data=data)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    async def test_token_expired(self) -> None:
        """만료된 토큰 디코딩 시 JWTError가 발생한다."""
        data = {"sub": "testuser", "role": "viewer"}
        token = create_access_token(data=data, expires_delta=timedelta(seconds=-1))
        with pytest.raises(Exception):  # jose.ExpiredSignatureError
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# --- TestRegister ---


class TestRegister:
    """사용자 등록 테스트"""

    async def test_register_success(self, auth_service: AuthService, async_session, sample_user_create) -> None:
        """정상적으로 사용자를 등록한다."""
        user = await auth_service.register(async_session, sample_user_create)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "viewer"
        assert user.is_active is True
        assert user.hashed_password != sample_user_create.password

    async def test_register_duplicate_username(
        self, auth_service: AuthService, async_session, sample_user_create
    ) -> None:
        """중복된 username으로 등록 시 409 에러가 발생한다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        duplicate_user = UserCreate(
            username="testuser",
            email="other@example.com",
            password="securepass456",
        )
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register(async_session, duplicate_user)
        assert exc_info.value.status_code == 409
        assert "사용자명" in exc_info.value.detail

    async def test_register_duplicate_email(self, auth_service: AuthService, async_session, sample_user_create) -> None:
        """중복된 email로 등록 시 409 에러가 발생한다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        duplicate_user = UserCreate(
            username="otheruser",
            email="test@example.com",
            password="securepass456",
        )
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register(async_session, duplicate_user)
        assert exc_info.value.status_code == 409
        assert "이메일" in exc_info.value.detail


# --- TestAuthenticate ---


class TestAuthenticate:
    """사용자 인증 테스트"""

    async def test_authenticate_success(self, auth_service: AuthService, async_session, sample_user_create) -> None:
        """올바른 자격증명으로 인증에 성공한다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        user = await auth_service.authenticate(async_session, "testuser", "securepass123")
        assert user is not None
        assert user.username == "testuser"

    async def test_authenticate_wrong_password(
        self, auth_service: AuthService, async_session, sample_user_create
    ) -> None:
        """잘못된 비밀번호로 인증 시 None을 반환한다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        user = await auth_service.authenticate(async_session, "testuser", "wrongpassword")
        assert user is None

    async def test_authenticate_nonexistent_user(self, auth_service: AuthService, async_session) -> None:
        """존재하지 않는 사용자로 인증 시 None을 반환한다."""
        user = await auth_service.authenticate(async_session, "nonexistent", "password123")
        assert user is None


# --- TestLogin ---


class TestLogin:
    """로그인 테스트"""

    async def test_login_success(self, auth_service: AuthService, async_session, sample_user_create) -> None:
        """정상 로그인 시 access_token과 refresh_token이 반환된다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        access_token, refresh_token = await auth_service.login(async_session, "testuser", "securepass123")
        assert access_token is not None
        assert refresh_token is not None

        # 토큰 디코딩 검증
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["role"] == "viewer"

    async def test_login_updates_last_login_at(
        self, auth_service: AuthService, async_session, sample_user_create
    ) -> None:
        """로그인 시 last_login_at이 업데이트된다."""
        user = await auth_service.register(async_session, sample_user_create)
        await async_session.flush()
        assert user.last_login_at is None

        await auth_service.login(async_session, "testuser", "securepass123")
        await async_session.flush()

        # 업데이트 확인을 위해 refresh
        await async_session.refresh(user)
        assert user.last_login_at is not None

    async def test_login_invalid_credentials(self, auth_service: AuthService, async_session) -> None:
        """잘못된 자격증명으로 로그인 시 401 에러가 발생한다."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(async_session, "nonexistent", "password")
        assert exc_info.value.status_code == 401


# --- TestRefreshToken ---


class TestRefreshToken:
    """토큰 갱신 테스트"""

    async def test_refresh_token_success(self, auth_service: AuthService, async_session, sample_user_create) -> None:
        """유효한 리프레시 토큰으로 새 토큰 쌍을 받는다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        _, refresh_token = await auth_service.login(async_session, "testuser", "securepass123")
        await async_session.flush()

        new_access_token, new_refresh_token = await auth_service.refresh_token(async_session, refresh_token)
        assert new_access_token is not None
        assert new_refresh_token is not None

        # 새 액세스 토큰 디코딩 검증
        payload = jwt.decode(new_access_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "testuser"

    async def test_refresh_token_invalid(self, auth_service: AuthService, async_session) -> None:
        """유효하지 않은 리프레시 토큰으로 갱신 시 401 에러가 발생한다."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(async_session, "invalid-token-string")
        assert exc_info.value.status_code == 401

    async def test_refresh_token_with_access_token(
        self, auth_service: AuthService, async_session, sample_user_create
    ) -> None:
        """액세스 토큰(type=refresh 아님)으로 갱신 시 401 에러가 발생한다."""
        await auth_service.register(async_session, sample_user_create)
        await async_session.flush()

        access_token, _ = await auth_service.login(async_session, "testuser", "securepass123")
        await async_session.flush()

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(async_session, access_token)
        assert exc_info.value.status_code == 401
