from datetime import UTC, datetime

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import _get_jwt_secret, create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate


class AuthService:
    """인증 관련 비즈니스 로직"""

    async def register(self, db: AsyncSession, user_create: UserCreate) -> User:
        """사용자를 등록한다. 중복 username/email이면 409를 발생시킨다."""
        # username 중복 확인
        result = await db.execute(select(User).where(User.username == user_create.username))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 사용자명입니다",
            )

        # email 중복 확인
        result = await db.execute(select(User).where(User.email == user_create.email))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 이메일입니다",
            )

        # 사용자 생성
        user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=get_password_hash(user_create.password),
            role=UserRole.VIEWER,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.commit()
        await db.refresh(user)
        return user

    async def authenticate(self, db: AsyncSession, username: str, password: str) -> User | None:
        """username과 비밀번호로 사용자를 인증한다. 실패하면 None을 반환한다."""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, db: AsyncSession, username: str, password: str) -> tuple[str, str]:
        """로그인 후 (access_token, refresh_token) 쌍을 반환한다. 실패하면 401을 발생시킨다."""
        user = await self.authenticate(db, username, password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자명 또는 비밀번호가 올바르지 않습니다",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # last_login_at 업데이트
        user.last_login_at = datetime.now(UTC)
        await db.flush()
        await db.commit()

        # 토큰 생성
        token_data = {"sub": user.username, "role": user.role}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        return access_token, refresh_token

    async def refresh_token(self, db: AsyncSession, refresh_token: str) -> tuple[str, str]:
        """리프레시 토큰을 검증하고 새 토큰 쌍을 반환한다. 유효하지 않으면 401을 발생시킨다."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(refresh_token, _get_jwt_secret(), algorithms=[settings.JWT_ALGORITHM])
            username: str | None = payload.get("sub")
            token_type: str | None = payload.get("type")
            if username is None or token_type != "refresh":
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        # 사용자 존재 확인
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception

        # 새 토큰 쌍 생성
        token_data = {"sub": user.username, "role": user.role}
        new_access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(data=token_data)
        return new_access_token, new_refresh_token
