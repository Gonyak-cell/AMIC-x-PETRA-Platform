"""인증 서비스 — 로그인, 회원가입, 토큰 갱신.

FDD-1701 (RBAC) + FDD-1704 (세션/토큰 관리).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.password import hash_password, verify_password
from app.auth.token import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    is_token_blacklisted,
)
from app.core.errors import ErrorCode
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.models.audit import AuditAction, AuditLog
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User, UserRole

logger = get_logger(__name__)


def register_user(
    db: Session,
    email: str,
    password: str,
    display_name: str,
    role: UserRole = UserRole.ANALYST,
    title: str = "",
) -> User:
    """새 사용자를 등록한다."""
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise AuthenticationError(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            "Email already registered",
        )

    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
        title=title,
        role=role,
    )
    db.add(user)
    db.flush()

    db.add(
        AuditLog(
            entity_type="user",
            entity_id=user.id,
            action=AuditAction.CREATE,
            actor=email,
            user_id=user.id,
            new_value={"email": email, "role": role.value},
        )
    )

    db.commit()
    db.refresh(user)
    logger.info("User registered", extra={"ctx": {"email": email, "role": role.value}})
    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[str, str]:
    """사용자를 인증하고 (access_token, refresh_token) 튜플을 반환한다."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            "Invalid email or password",
        )
    if not user.is_active:
        raise AuthenticationError(
            ErrorCode.AUTH_USER_DISABLED,
            "User account is disabled",
        )

    user.last_login_at = datetime.now(UTC)
    db.commit()

    access = create_access_token(user.id, user.email, user.role.value)
    refresh = create_refresh_token(user.id)
    logger.info("User authenticated", extra={"ctx": {"email": email}})
    return access, refresh


def refresh_tokens(
    db: Session,
    refresh_token: str,
) -> tuple[str, str]:
    """Refresh Token으로 새 토큰 쌍을 발급한다.

    구 refresh token은 블랙리스트에 등록하여 재사용을 방지한다.
    """
    payload = decode_refresh_token(refresh_token)
    user_id = uuid.UUID(payload["sub"])

    # 블랙리스트 체크 (refresh token 재사용 방지)
    old_jti = payload.get("jti")
    if old_jti and is_token_blacklisted(db, old_jti):
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_REVOKED,
            "Refresh token has been revoked",
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "User not found or disabled",
        )

    # 구 refresh token 블랙리스트 등록
    if old_jti:
        old_exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)
        db.add(
            TokenBlacklist(
                jti=old_jti,
                user_id=user_id,
                token_type="refresh",
                expires_at=old_exp,
            )
        )
        db.flush()

    access = create_access_token(user.id, user.email, user.role.value)
    refresh = create_refresh_token(user.id)
    db.commit()
    return access, refresh


def list_users(db: Session) -> list[User]:
    """전체 사용자 목록을 반환한다."""
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


def update_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    display_name: str | None = None,
    title: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    actor_email: str = "system",
) -> User:
    """사용자 정보를 수정한다."""
    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "User not found",
        )

    old_values: dict[str, str | bool] = {}
    new_values: dict[str, str | bool] = {}

    if display_name is not None:
        old_values["display_name"] = user.display_name
        user.display_name = display_name
        new_values["display_name"] = display_name

    if title is not None:
        old_values["title"] = user.title
        user.title = title
        new_values["title"] = title

    if role is not None:
        old_values["role"] = user.role.value
        user.role = role
        new_values["role"] = role.value

    if is_active is not None:
        old_values["is_active"] = user.is_active
        user.is_active = is_active
        new_values["is_active"] = is_active

    if new_values:
        db.add(
            AuditLog(
                entity_type="user",
                entity_id=user.id,
                action=AuditAction.UPDATE,
                actor=actor_email,
                user_id=user.id,
                old_value=old_values,
                new_value=new_values,
            )
        )

    db.commit()
    db.refresh(user)
    return user


def delete_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    actor_email: str = "system",
) -> None:
    """사용자를 삭제한다 (Admin 전용)."""
    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "User not found",
        )

    email = user.email
    role = user.role.value

    # 감사 로그 먼저 기록 (삭제 전)
    db.add(
        AuditLog(
            entity_type="user",
            entity_id=user.id,
            action=AuditAction.DELETE,
            actor=actor_email,
            user_id=None,  # 삭제될 사용자 참조 방지
            old_value={"email": email, "role": role},
        )
    )

    db.delete(user)
    db.commit()
    logger.info("User deleted", extra={"ctx": {"email": email, "actor": actor_email}})


def logout_user(
    db: Session,
    user_id: uuid.UUID,
    jti: str,
    token_exp: datetime,
    user_email: str,
) -> None:
    """현재 Access Token을 블랙리스트에 등록한다 (로그아웃)."""
    db.add(
        TokenBlacklist(
            jti=jti,
            user_id=user_id,
            token_type="access",
            expires_at=token_exp,
        )
    )
    db.add(
        AuditLog(
            entity_type="user",
            entity_id=user_id,
            action=AuditAction.LOGOUT,
            actor=user_email,
            user_id=user_id,
            new_value={"jti": jti},
        )
    )
    db.commit()
    logger.info("User logged out", extra={"ctx": {"email": user_email, "jti": jti}})


def cleanup_expired_blacklist(db: Session) -> int:
    """만료된 블랙리스트 항목을 삭제한다.

    Returns:
        삭제된 레코드 수.
    """
    result = db.execute(
        delete(TokenBlacklist).where(
            TokenBlacklist.expires_at < datetime.now(UTC)
        )
    )
    db.commit()
    count = result.rowcount
    logger.info("Cleaned up %d expired blacklist entries", count)
    return count
