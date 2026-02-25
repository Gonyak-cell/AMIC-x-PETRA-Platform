"""인증 API — /api/v1/auth/*.

FDD-1701 (RBAC) + FDD-1704 (세션/토큰 관리).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_permission
from app.auth.rbac import Permission
from app.auth.token import decode_access_token
from app.config import settings
from app.core.errors import ErrorCode
from app.core.exceptions import AuthenticationError
from app.database import get_db
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.auth_service import (
    authenticate_user,
    delete_user,
    list_users,
    logout_user,
    refresh_tokens,
    register_user,
    update_user,
)

_bearer_scheme = HTTPBearer(auto_error=False)
_is_production = os.getenv("ENV", "").lower() in ("production", "prod")
_cookie_secure = _is_production  # HTTPS only in production

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """사용자 로그인 — JWT 토큰을 httpOnly 쿠키로 설정."""
    access, refresh = authenticate_user(db, body.email, body.password)

    # Access Token 세션 쿠키 설정 (브라우저 종료 시 삭제)
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=_cookie_secure,
        samesite="lax",
    )

    # Refresh Token 세션 쿠키 설정 (브라우저 종료 시 삭제)
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=_cookie_secure,
        samesite="lax",
    )

    return {"message": "로그인 성공"}


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Access Token 갱신 — httpOnly 쿠키에서 refresh_token을 읽어 갱신."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Refresh token not found in cookies",
        )
    access, refresh_tok = refresh_tokens(db, refresh_token)

    # Access Token 세션 쿠키 설정 (브라우저 종료 시 삭제)
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=_cookie_secure,
        samesite="lax",
    )

    # Refresh Token 세션 쿠키 설정 (브라우저 종료 시 삭제)
    response.set_cookie(
        key="refresh_token",
        value=refresh_tok,
        httponly=True,
        secure=_cookie_secure,
        samesite="lax",
    )

    return {"message": "토큰 갱신 성공"}


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Response:
    """현재 Access Token을 무효화한다 (로그아웃)."""
    # 쿠키 삭제
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    if credentials is None:
        return response

    payload = decode_access_token(credentials.credentials)
    jti = payload.get("jti")
    if not jti:
        # jti 없는 레거시 토큰은 블랙리스트 등록 불가
        return response

    token_exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)
    logout_user(db, current_user.id, jti, token_exp, current_user.email)
    return response


@router.post("/change-password", status_code=204)
def change_password(
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """현재 사용자의 비밀번호를 변경한다."""
    from app.auth.password import hash_password, verify_password
    from app.models.user import User

    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")

    if not current_password or not new_password:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Current password and new password are required",
        )

    user = db.get(User, current_user.id)
    if user is None:
        raise AuthenticationError(ErrorCode.AUTH_TOKEN_INVALID, "User not found")

    if not verify_password(current_password, user.hashed_password):
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID, "Current password is incorrect"
        )

    user.hashed_password = hash_password(new_password)
    db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """현재 로그인 사용자 프로필 조회."""
    from app.models.user import User

    user = db.get(User, current_user.id)
    if user is None:
        # dev 모드에서는 임시 응답 (DB에 사용자가 없음)
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        return UserRead(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            title="",
            role=current_user.role,
            is_active=True,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
    return user


@router.get("/users", response_model=list[UserRead])
def get_users(
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """전체 사용자 목록 조회 (Admin 전용)."""
    return list_users(db)


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(
    body: UserCreate,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """새 사용자 생성 (Admin 전용)."""
    return register_user(db, body.email, body.password, body.display_name, body.role, body.title)


@router.put("/users/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
):
    """사용자 정보 수정 (Admin 전용)."""
    return update_user(
        db,
        user_id,
        display_name=body.display_name,
        title=body.title,
        role=body.role,
        is_active=body.is_active,
        actor_email=current_user.email,
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: uuid.UUID,
    current_user: CurrentUser = require_permission(Permission.USER_MANAGE),
    db: Session = Depends(get_db),
) -> Response:
    """사용자를 삭제한다 (Admin 전용). 본인 삭제 방지."""
    if current_user.id == user_id:
        raise AuthenticationError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "Cannot delete your own account",
        )
    delete_user(db, user_id, actor_email=current_user.email)
    return Response(status_code=204)
