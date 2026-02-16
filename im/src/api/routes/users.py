"""사용자 관리 엔드포인트.

> 마지막 수정: 2026-02-10 19:30:00

GET   /api/v1/users/me          — 내 프로필
PATCH /api/v1/users/me          — 내 프로필 수정
POST  /api/v1/users             — 사용자 생성 (ADMIN)
GET   /api/v1/users             — 사용자 목록 (ADMIN)
GET   /api/v1/users/{user_id}   — 사용자 상세 (ADMIN)
PATCH /api/v1/users/{user_id}   — 사용자 수정 (ADMIN)
DELETE /api/v1/users/{user_id}  — 사용자 비활성화 (ADMIN)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.user import (
    AdminUserUpdateRequest,
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from src.api.security.rbac import require_admin
from src.api.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


async def _get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """ADMIN 역할을 요구하는 의존성."""
    require_admin(current_user)
    return current_user


# ============================================================================
# 본인 프로필 엔드포인트
# ============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="내 프로필 조회",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """현재 인증된 사용자의 프로필을 반환한다."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="내 프로필 수정",
)
async def update_me(
    data: UserUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """자신의 프로필(이름, 비밀번호)을 수정한다."""
    service = UserService(session)
    user = await service.update_me(current_user.id, data)
    return UserResponse.model_validate(user)


# ============================================================================
# ADMIN 전용 엔드포인트
# ============================================================================


@router.post(
    "",
    response_model=UserResponse,
    status_code=201,
    summary="사용자 생성 (ADMIN)",
)
async def create_user(
    data: UserCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    admin_user: User = Depends(_get_admin_user),
) -> UserResponse:
    """ADMIN이 새 사용자를 생성한다."""
    service = UserService(session)
    user = await service.create_user(data)
    return UserResponse.model_validate(user)


@router.get(
    "",
    response_model=UserListResponse,
    summary="사용자 목록 (ADMIN)",
)
async def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    active_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_async_session),
    admin_user: User = Depends(_get_admin_user),
) -> UserListResponse:
    """사용자 목록을 조회한다 (ADMIN 전용)."""
    service = UserService(session)
    items, total = await service.list_users(offset, limit, active_only)
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 상세 (ADMIN)",
)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    admin_user: User = Depends(_get_admin_user),
) -> UserResponse:
    """특정 사용자를 조회한다 (ADMIN 전용)."""
    service = UserService(session)
    user = await service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="사용자 수정 (ADMIN)",
)
async def admin_update_user(
    user_id: UUID,
    data: AdminUserUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    admin_user: User = Depends(_get_admin_user),
) -> UserResponse:
    """ADMIN이 사용자 역할/활성 상태를 수정한다."""
    service = UserService(session)
    user = await service.admin_update(user_id, data)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="사용자 비활성화 (ADMIN)",
)
async def deactivate_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    admin_user: User = Depends(_get_admin_user),
) -> Response:
    """사용자를 비활성화한다 (soft delete, ADMIN 전용)."""
    service = UserService(session)
    await service.deactivate(user_id)
    return Response(status_code=204)
