"""JWT 토큰 생성/검증 유닛 테스트."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from app.auth.token import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.config import settings
from app.core.exceptions import AuthenticationError


class TestAccessToken:
    def test_create_and_decode_roundtrip(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, "test@test.com", "ADMIN")
        payload = decode_access_token(token)
        assert payload["sub"] == str(uid)
        assert payload["email"] == "test@test.com"
        assert payload["role"] == "ADMIN"
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        uid = uuid.uuid4()
        payload = {
            "sub": str(uid),
            "email": "t@t.com",
            "role": "ANALYST",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(token)
        assert exc_info.value.code.value == 9011  # AUTH_TOKEN_EXPIRED

    def test_invalid_token_raises(self):
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token("garbage.token.value")
        assert exc_info.value.code.value == 9012  # AUTH_TOKEN_INVALID

    def test_refresh_token_as_access_rejected(self):
        uid = uuid.uuid4()
        token = create_refresh_token(uid)
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(token)
        assert exc_info.value.code.value == 9012  # AUTH_TOKEN_INVALID

    def test_token_contains_iat_claim(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, "test@test.com", "VIEWER")
        payload = decode_access_token(token)
        assert "iat" in payload


class TestRefreshToken:
    def test_create_and_decode_roundtrip(self):
        uid = uuid.uuid4()
        token = create_refresh_token(uid)
        payload = decode_refresh_token(token)
        assert payload["sub"] == str(uid)
        assert payload["type"] == "refresh"

    def test_expired_refresh_raises(self):
        uid = uuid.uuid4()
        payload = {
            "sub": str(uid),
            "type": "refresh",
            "exp": datetime.now(UTC) - timedelta(days=1),
            "iat": datetime.now(UTC) - timedelta(days=8),
        }
        token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(AuthenticationError) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.code.value == 9013  # AUTH_REFRESH_TOKEN_EXPIRED

    def test_access_token_as_refresh_rejected(self):
        uid = uuid.uuid4()
        token = create_access_token(uid, "t@t.com", "ADMIN")
        with pytest.raises(AuthenticationError) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.code.value == 9012  # AUTH_TOKEN_INVALID
