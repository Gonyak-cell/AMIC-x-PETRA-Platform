"""초대 서비스 — CLIENT 사용자 초대 + 토큰 관리."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.config import settings
from app.core.errors import ErrorCode
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.models.audit import AuditAction, AuditLog
from app.models.invite_token import InviteStatus, InviteToken
from app.models.user import User, UserRole
from app.services.email_service import send_invite_email

logger = get_logger(__name__)


def _expire_pending_tokens(db: Session, user_id: uuid.UUID) -> None:
    """사용자의 모든 PENDING 초대 토큰을 EXPIRED로 변경한다."""
    pending = db.scalars(
        select(InviteToken).where(
            InviteToken.user_id == user_id,
            InviteToken.status == InviteStatus.PENDING,
        )
    ).all()
    for tok in pending:
        tok.status = InviteStatus.EXPIRED
    if pending:
        db.flush()


def _issue_invite_token(db: Session, user_id: uuid.UUID) -> str:
    """새 초대 토큰을 발급한다. 기존 PENDING 토큰은 만료 처리한다."""
    _expire_pending_tokens(db, user_id)

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.invite_token_expire_hours)
    invite = InviteToken(
        user_id=user_id,
        token=raw_token,
        status=InviteStatus.PENDING,
        expires_at=expires_at,
    )
    db.add(invite)
    db.flush()
    return raw_token


def create_invite(
    db: Session,
    *,
    email: str,
    display_name: str,
    title: str,
    transaction_ids: list[uuid.UUID],
    transaction_names: list[str],
    actor_email: str,
) -> dict:
    """CLIENT 사용자를 초대한다.

    - 이미 존재하는 비CLIENT 사용자 → 에러
    - 이미 활성화된 CLIENT → invite_sent=False 조기 반환
    - 비활성 CLIENT → 재사용 (토큰 재발급)
    - 신규 → 생성 (is_active=False)
    """
    normalized_email = email.lower().strip()

    existing: User | None = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    is_new_user = False

    if existing is not None:
        if existing.role != UserRole.CLIENT:
            raise AuthenticationError(
                ErrorCode.AUTH_FORBIDDEN,
                f"User {normalized_email} already exists with non-CLIENT role: {existing.role.value}",
            )
        if existing.is_active:
            return {
                "user_id": existing.id,
                "email": existing.email,
                "display_name": existing.display_name,
                "is_new_user": False,
                "assigned_deal_count": len(transaction_ids),
                "invite_sent": False,
                "invite_error": "이미 활성화된 CLIENT",
            }
        user = existing
    else:
        is_new_user = True
        user = User(
            email=normalized_email,
            hashed_password=hash_password(secrets.token_urlsafe(24)),
            display_name=display_name,
            title=title,
            role=UserRole.CLIENT,
            is_active=False,
        )
        db.add(user)
        db.flush()
        db.add(
            AuditLog(
                entity_type="user",
                entity_id=user.id,
                action=AuditAction.CREATE,
                actor=actor_email,
                user_id=user.id,
                new_value={
                    "email": normalized_email,
                    "role": UserRole.CLIENT.value,
                    "is_active": False,
                },
            )
        )

    raw_token = _issue_invite_token(db, user.id)

    db.add(
        AuditLog(
            entity_type="invite_token",
            entity_id=user.id,
            action=AuditAction.CREATE,
            actor=actor_email,
            user_id=user.id,
            new_value={
                "email": normalized_email,
                "transaction_ids": [str(tid) for tid in transaction_ids],
            },
        )
    )

    db.commit()
    db.refresh(user)

    invite_url = f"{settings.frontend_url}/invite/accept?token={raw_token}"
    invite_sent = False
    invite_error: str | None = None

    try:
        send_invite_email(
            to_email=normalized_email,
            display_name=user.display_name,
            invite_url=invite_url,
            transaction_names=transaction_names,
        )
        invite_sent = True
    except Exception as exc:
        invite_error = str(exc)
        logger.warning(
            "Failed to send invite email",
            extra={"ctx": {"to": normalized_email, "error": invite_error}},
        )

    return {
        "user_id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_new_user": is_new_user,
        "assigned_deal_count": len(transaction_ids),
        "invite_sent": invite_sent,
        "invite_error": invite_error,
    }


def _aware(dt: datetime) -> datetime:
    """timezone-naive datetime을 UTC aware로 변환한다 (SQLite 호환)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def verify_invite_token(db: Session, token: str) -> dict:
    """초대 토큰의 유효성을 검증한다."""
    invite: InviteToken | None = db.scalar(
        select(InviteToken).where(InviteToken.token == token)
    )

    if invite is None:
        return {"valid": False, "expired": False, "already_used": False}

    if invite.status == InviteStatus.ACCEPTED:
        return {"valid": False, "expired": False, "already_used": True}

    if invite.status == InviteStatus.EXPIRED or datetime.now(UTC) > _aware(
        invite.expires_at
    ):
        return {"valid": False, "expired": True, "already_used": False}

    user: User | None = db.get(User, invite.user_id)
    if user is None:
        return {"valid": False, "expired": False, "already_used": False}

    return {
        "valid": True,
        "email": user.email,
        "display_name": user.display_name,
        "expired": False,
        "already_used": False,
    }


def accept_invite(db: Session, token: str, password: str) -> dict:
    """초대를 수락하고 비밀번호를 설정한다."""
    invite: InviteToken | None = db.scalar(
        select(InviteToken).where(InviteToken.token == token)
    )

    if invite is None:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Invalid invite token",
        )

    if invite.status == InviteStatus.ACCEPTED:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Invite token has already been used",
        )

    if invite.status == InviteStatus.EXPIRED or datetime.now(UTC) > _aware(
        invite.expires_at
    ):
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_EXPIRED,
            "Invite token has expired",
        )

    user: User | None = db.get(User, invite.user_id)
    if user is None:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Associated user not found",
        )

    user.hashed_password = hash_password(password)
    user.is_active = True

    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = datetime.now(UTC)

    db.add(
        AuditLog(
            entity_type="user",
            entity_id=user.id,
            action=AuditAction.UPDATE,
            actor=user.email,
            user_id=user.id,
            old_value={"is_active": False},
            new_value={"is_active": True},
        )
    )

    db.commit()
    logger.info("Invite accepted", extra={"ctx": {"email": user.email}})

    return {"message": "초대 수락 완료. 로그인하세요.", "email": user.email}
