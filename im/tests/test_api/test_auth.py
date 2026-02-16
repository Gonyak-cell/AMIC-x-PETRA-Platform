"""JWT RS256 인증 테스트 (T-I07).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest

from src.api.config import APIConfig
from src.api.exceptions import AuthenticationError
from src.api.security.auth import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    verify_token,
)


@pytest.fixture
def hs256_config() -> APIConfig:
    """HS256 폴백용 테스트 설정."""
    return APIConfig(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
        redis_url="redis://localhost:6380/15",
        redis_result_backend="redis://localhost:6380/14",
        jwt_secret_key="test-secret-key-for-jwt-tests-min32",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=30,
        jwt_refresh_token_expire_days=7,
    )


@pytest.fixture
def user_id() -> str:
    """테스트용 사용자 ID."""
    return str(uuid.uuid4())


class TestCreateAccessToken:
    """Access token 생성 테스트."""

    def test_creates_valid_token(self, hs256_config: APIConfig, user_id: str) -> None:
        """정상적인 access token을 생성한다."""
        token = create_access_token(user_id, "USER", config=hs256_config)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_correct_claims(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """생성된 토큰에 올바른 클레임이 포함된다."""
        token = create_access_token(user_id, "ADMIN", config=hs256_config)
        payload = verify_token(token, config=hs256_config)

        assert payload.sub == user_id
        assert payload.role == "ADMIN"
        assert payload.token_type == "access"
        assert isinstance(payload.jti, str)
        assert len(payload.jti) > 0


class TestCreateRefreshToken:
    """Refresh token 생성 테스트."""

    def test_creates_valid_refresh_token(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """정상적인 refresh token을 생성한다."""
        token = create_refresh_token(user_id, config=hs256_config)
        payload = verify_token(token, config=hs256_config)

        assert payload.sub == user_id
        assert payload.token_type == "refresh"

    def test_refresh_token_has_longer_expiry(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """Refresh token은 access token보다 긴 만료 시간을 가진다."""
        access = create_access_token(user_id, "USER", config=hs256_config)
        refresh = create_refresh_token(user_id, config=hs256_config)

        access_payload = verify_token(access, config=hs256_config)
        refresh_payload = verify_token(refresh, config=hs256_config)

        assert refresh_payload.exp > access_payload.exp


class TestVerifyToken:
    """토큰 검증 테스트."""

    def test_verify_valid_access_token(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """유효한 access token을 검증한다."""
        token = create_access_token(user_id, "USER", config=hs256_config)
        payload = verify_token(token, config=hs256_config, expected_type="access")

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id

    def test_expired_token_rejected(self, hs256_config: APIConfig, user_id: str) -> None:
        """만료된 토큰을 거부한다."""
        expired_config = APIConfig(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
            redis_url="redis://localhost:6380/15",
            redis_result_backend="redis://localhost:6380/14",
            jwt_secret_key="test-secret-key-for-jwt-tests-min32",
            jwt_algorithm="HS256",
            jwt_access_token_expire_minutes=1,
        )
        # 직접 만료된 토큰 생성
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "role": "USER",
            "exp": now - timedelta(seconds=10),
            "iat": now - timedelta(minutes=31),
            "jti": str(uuid.uuid4()),
            "token_type": "access",
        }
        token = jwt.encode(payload, "test-secret-key-for-jwt-tests-min32", algorithm="HS256")

        with pytest.raises(AuthenticationError, match="만료"):
            verify_token(token, config=expired_config)

    def test_tampered_token_rejected(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """변조된 토큰을 거부한다."""
        token = create_access_token(user_id, "USER", config=hs256_config)
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(AuthenticationError, match="유효하지 않은"):
            verify_token(tampered, config=hs256_config)

    def test_wrong_key_rejected(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """잘못된 키로 서명된 토큰을 거부한다."""
        token = create_access_token(user_id, "USER", config=hs256_config)

        wrong_key_config = APIConfig(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
            redis_url="redis://localhost:6380/15",
            redis_result_backend="redis://localhost:6380/14",
            jwt_secret_key="completely-different-secret-key-min32b",
            jwt_algorithm="HS256",
        )

        with pytest.raises(AuthenticationError, match="유효하지 않은"):
            verify_token(token, config=wrong_key_config)

    def test_jti_uniqueness(self, hs256_config: APIConfig, user_id: str) -> None:
        """각 토큰의 JTI가 고유하다."""
        token1 = create_access_token(user_id, "USER", config=hs256_config)
        token2 = create_access_token(user_id, "USER", config=hs256_config)

        payload1 = verify_token(token1, config=hs256_config)
        payload2 = verify_token(token2, config=hs256_config)

        assert payload1.jti != payload2.jti

    def test_wrong_token_type_rejected(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """Access token으로 refresh 검증 시 거부한다."""
        access = create_access_token(user_id, "USER", config=hs256_config)

        with pytest.raises(AuthenticationError, match="잘못된 토큰 타입"):
            verify_token(access, config=hs256_config, expected_type="refresh")

    def test_refresh_as_access_rejected(
        self, hs256_config: APIConfig, user_id: str
    ) -> None:
        """Refresh token으로 access 검증 시 거부한다."""
        refresh = create_refresh_token(user_id, config=hs256_config)

        with pytest.raises(AuthenticationError, match="잘못된 토큰 타입"):
            verify_token(refresh, config=hs256_config, expected_type="access")

    def test_missing_claims_rejected(self, hs256_config: APIConfig) -> None:
        """필수 클레임이 누락된 토큰을 거부한다."""
        incomplete_payload = {
            "sub": "some-user",
            # role, jti, token_type 누락
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(
            incomplete_payload, "test-secret-key-for-jwt-tests-min32", algorithm="HS256"
        )

        with pytest.raises(AuthenticationError, match="유효하지 않은"):
            verify_token(token, config=hs256_config)


class TestHS256Fallback:
    """HS256 폴백 테스트."""

    def test_hs256_fallback_when_no_pem(self, user_id: str) -> None:
        """PEM 파일이 없으면 HS256으로 폴백한다."""
        config = APIConfig(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
            redis_url="redis://localhost:6380/15",
            redis_result_backend="redis://localhost:6380/14",
            jwt_secret_key="hs256-fallback-key-minimum-32-bytes-long",
            jwt_algorithm="RS256",
            jwt_private_key_path="nonexistent/private.pem",
            jwt_public_key_path="nonexistent/public.pem",
        )

        token = create_access_token(user_id, "USER", config=config)
        payload = verify_token(token, config=config)

        assert payload.sub == user_id
        assert payload.token_type == "access"
