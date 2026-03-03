"""API 키 관리 엔드포인트.

> 마지막 수정: 2026-02-10 19:30:00

POST   /api/v1/api-keys           — API 키 생성
GET    /api/v1/api-keys           — API 키 목록
DELETE /api/v1/api-keys/{key_id}  — API 키 비활성화
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from src.api.services.api_key_service import APIKeyService

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    status_code=201,
    summary="API 키 생성",
    description="새 API 키를 생성한다. 평문 키는 이 응답에서만 노출된다.",
)
async def create_api_key(
    data: APIKeyCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> APIKeyCreateResponse:
    """새 API 키를 생성한다."""
    service = APIKeyService(session)
    api_key, raw_key = await service.create(
        user_id=current_user.id,
        name=data.name,
        expires_days=data.expires_days,
    )
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get(
    "",
    response_model=APIKeyListResponse,
    summary="API 키 목록",
)
async def list_api_keys(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> APIKeyListResponse:
    """자신의 API 키 목록을 조회한다."""
    service = APIKeyService(session)
    items, total = await service.list_keys(current_user.id)
    return APIKeyListResponse(
        items=[APIKeyResponse.model_validate(k) for k in items],
        total=total,
    )


@router.delete(
    "/{key_id}",
    status_code=204,
    response_class=Response,
    summary="API 키 비활성화",
)
async def revoke_api_key(
    key_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """API 키를 비활성화한다."""
    service = APIKeyService(session)
    await service.revoke(key_id, current_user.id)
    return Response(status_code=204)
