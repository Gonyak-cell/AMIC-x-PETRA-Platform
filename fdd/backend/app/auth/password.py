"""비밀번호 해싱 유틸리티 — bcrypt."""

import hmac

import bcrypt


def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 해싱한다."""
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    """비밀번호를 bcrypt 해시와 상수 시간 비교로 검증한다."""
    computed = bcrypt.hashpw(password.encode(), hashed.encode())
    return hmac.compare_digest(computed, hashed.encode())
