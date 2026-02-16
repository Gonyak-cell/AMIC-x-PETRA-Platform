"""사용자 서비스 레이어.

> 마지막 수정: 2026-02-10 19:30:00

사용자 CRUD 비즈니스 로직 (ADMIN 생성, 프로필 수정, 목록).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.user import User
from src.api.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.api.schemas.user import AdminUserUpdateRequest, UserCreateRequest, UserUpdateRequest
from src.api.security.password import hash_password, verify_password


class UserService:
    """사용자 관련 비즈니스 로직."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, data: UserCreateRequest) -> User:
        """새 사용자를 생성한다 (ADMIN 전용).

        Args:
            data: 사용자 생성 요청 데이터.

        Returns:
            생성된 User 인스턴스.

        Raises:
            ConflictError: 이메일 중복.
        """
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if result.scalar_one_or_none() is not None:
            raise ConflictError("User", data.email)

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User:
        """ID로 사용자를 조회한다.

        Args:
            user_id: 사용자 UUID.

        Returns:
            User 인스턴스.

        Raises:
            NotFoundError: 사용자가 없을 때.
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def update_me(
        self,
        user_id: UUID,
        data: UserUpdateRequest,
    ) -> User:
        """자신의 프로필을 수정한다.

        Args:
            user_id: 사용자 UUID.
            data: 수정 요청 데이터.

        Returns:
            수정된 User 인스턴스.

        Raises:
            AuthenticationError: 현재 비밀번호 불일치.
            ValidationError: new_password만 제공하고 current_password 없음.
        """
        user = await self.get_by_id(user_id)

        if data.full_name is not None:
            user.full_name = data.full_name

        if data.new_password is not None:
            if data.current_password is None:
                raise ValidationError(
                    field="current_password",
                    reason="비밀번호 변경 시 현재 비밀번호가 필요합니다",
                )
            if not verify_password(data.current_password, user.hashed_password):
                raise AuthenticationError(
                    message="현재 비밀번호가 올바르지 않습니다.",
                    details={"reason": "wrong_current_password"},
                )
            user.hashed_password = hash_password(data.new_password)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 20,
        active_only: bool = False,
    ) -> tuple[list[User], int]:
        """사용자 목록을 조회한다 (ADMIN 전용).

        Args:
            offset: 시작 오프셋.
            limit: 페이지 크기.
            active_only: True이면 활성 사용자만.

        Returns:
            (사용자 리스트, 전체 개수) 튜플.
        """
        base_query = select(User)
        if active_only:
            base_query = base_query.where(User.is_active.is_(True))

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        query = (
            base_query.order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def admin_update(
        self,
        target_id: UUID,
        data: AdminUserUpdateRequest,
    ) -> User:
        """관리자가 사용자 정보를 수정한다.

        Args:
            target_id: 대상 사용자 UUID.
            data: 수정 요청 데이터 (role, is_active).

        Returns:
            수정된 User 인스턴스.
        """
        user = await self.get_by_id(target_id)

        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def deactivate(self, target_id: UUID) -> None:
        """사용자를 비활성화한다 (soft delete).

        Args:
            target_id: 대상 사용자 UUID.
        """
        user = await self.get_by_id(target_id)
        user.is_active = False
        await self.db.commit()
