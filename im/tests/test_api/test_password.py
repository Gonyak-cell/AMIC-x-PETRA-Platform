"""비밀번호 해싱 유틸리티 테스트 (test_password.py).

> 마지막 수정: 2026-02-10 19:30:00

hash_password, verify_password 함수 검증.
"""

from __future__ import annotations

from src.api.security.password import hash_password, verify_password


def test_hash_password_returns_string() -> None:
    """hash_password는 문자열을 반환한다."""
    hashed = hash_password("mypassword123")
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_hash_different_each_time() -> None:
    """같은 입력도 salt로 인해 다른 해시를 생성한다."""
    plain = "testpassword"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)
    assert hash1 != hash2


def test_verify_password_correct() -> None:
    """올바른 평문 비밀번호는 검증에 성공한다."""
    plain = "correct_password"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_incorrect() -> None:
    """잘못된 평문 비밀번호는 검증에 실패한다."""
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False
