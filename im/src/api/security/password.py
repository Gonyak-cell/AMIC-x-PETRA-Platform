"""비밀번호 해싱 유틸리티.

> 마지막 수정: 2026-02-10 19:30:00

bcrypt 기반 비밀번호 해싱 및 검증을 제공한다.
"""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환한다.

    Args:
        plain: 평문 비밀번호.

    Returns:
        bcrypt 해시 문자열.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """평문 비밀번호와 해시를 비교한다.

    Args:
        plain: 평문 비밀번호.
        hashed: bcrypt 해시 문자열.

    Returns:
        일치하면 True, 아니면 False.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
