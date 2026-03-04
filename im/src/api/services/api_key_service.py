"""API 키 서비스 레이어.

> 마지막 수정: 2026-02-10 19:30:00

API 키 생성, 조회, 비활성화 비즈니스 로직.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.api_key import APIKey
from src.api.exceptions import AuthorizationError, NotFoundError
from src.api.security.api_keys import generate_api_key


class APIKeyService:
    """API 키 관련 비즈니스 로직."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: UUID,
        name: str,
        expires_days: int | None = None,
    ) -> tuple[APIKey, str]:
        """새 API 키를 생성한다.

        Args:
            user_id: 소유자 사용자 ID.
            name: 키 이름/용도.
            expires_days: 만료 일수 (None이면 영구).

        Returns:
            (APIKey 인스턴스, raw_key) 튜플. raw_key는 이때만 노출.
        """
        raw_key, key_hash = generate_api_key()

        expires_at: datetime | None = None
        if expires_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            is_active=True,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        return api_key, raw_key

    async def list_keys(self, user_id: UUID) -> tuple[list[APIKey], int]:
        """사용자의 API 키 목록을 조회한다.

        Args:
            user_id: 소유자 사용자 ID.

        Returns:
            (API 키 리스트, 전체 개수) 튜플.
        """
        base_query = select(APIKey).where(APIKey.user_id == user_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        query = base_query.order_by(APIKey.created_at.desc())
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def revoke(self, key_id: UUID, user_id: UUID) -> None:
        """API 키를 비활성화한다.

        Args:
            key_id: API 키 ID.
            user_id: 요청 사용자 ID (소유 확인).

        Raises:
            NotFoundError: 키가 없을 때.
            AuthorizationError: 본인 소유가 아닐 때.
        """
        result = await self.db.execute(select(APIKey).where(APIKey.id == key_id))
        api_key = result.scalar_one_or_none()

        if api_key is None:
            raise NotFoundError("APIKey", str(key_id))

        if api_key.user_id != user_id:
            raise AuthorizationError(message="본인의 API 키만 삭제할 수 있습니다.")

        api_key.is_active = False
        await self.db.commit()
