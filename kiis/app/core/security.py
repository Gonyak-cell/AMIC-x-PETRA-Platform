import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass(frozen=True)
class JWTClaims:
    """크로스 백엔드 JWT 클레임 (DB 조회 없이 사용)."""

    user_id: str
    email: str | None
    role: str


def _get_jwt_secret() -> str:
    """JWT 검증에 사용할 시크릿을 반환한다. JWT_SECRET 우선, 없으면 SECRET_KEY 폴백."""
    secret = settings.JWT_SECRET or settings.SECRET_KEY
    if not secret:
        raise RuntimeError(
            "JWT secret is not configured. "
            "Set JWT_SECRET or SECRET_KEY in your .env file."
        )
    return secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호를 비교한다."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """비밀번호를 bcrypt로 해시한다."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWT 액세스 토큰을 생성한다."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, _get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """JWT 리프레시 토큰을 생성한다."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt: str = jwt.encode(to_encode, _get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def _is_uuid(value: str) -> bool:
    """문자열이 UUID 형식인지 확인한다."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


async def get_jwt_claims(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> JWTClaims:
    """JWT 토큰에서 클레임만 추출한다 (DB 조회 없음).

    FDD 토큰을 디코딩하여 user_id, email, role을 반환한다.
    KIIS User DB를 조회하지 않으므로 경량 의존성으로 사용 가능.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Authorization 헤더 없으면 쿠키 폴백
    if token is None:
        token = request.cookies.get("access_token")
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[settings.JWT_ALGORITHM])
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return JWTClaims(
        user_id=sub,
        email=payload.get("email"),
        role=payload.get("role", ""),
    )


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """현재 인증된 사용자를 반환한다.

    FDD 토큰 (sub=UUID) → email로 KIIS User 조회.
    KIIS 토큰 (sub=username) → username으로 조회.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Authorization 헤더 없으면 쿠키 폴백
    if token is None:
        token = request.cookies.get("access_token")
    if token is None:
        raise credentials_exception

    # 1. JWT_SECRET으로 디코딩 시도, 실패 시 SECRET_KEY 폴백
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[settings.JWT_ALGORITHM])
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 2. sub가 UUID이면 FDD 토큰 → email로 KIIS User 조회
    if _is_uuid(sub):
        email: str | None = payload.get("email")
        if email:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is not None:
                return user
            # Cross-backend federation: FDD 토큰 정보로 KIIS 사용자 자동 생성
            role = payload.get("role", "analyst")
            # FDD 역할 → KIIS 역할 매핑 (대소문자 통일)
            role_lower = role.lower() if role else "analyst"
            if role_lower not in ("admin", "analyst", "viewer"):
                role_lower = "analyst"
            user = User(
                username=email.split("@")[0],
                email=email,
                hashed_password="federated:no-local-password",
                role=role_lower,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
        raise credentials_exception

    # 3. KIIS 자체 토큰 → username으로 조회 (기존 로직)
    result = await db.execute(select(User).where(User.username == sub))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """활성 상태인 현재 사용자를 반환한다. 비활성이면 400을 발생시킨다."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 사용자입니다",
        )
    return current_user


def require_role(*roles: str) -> Callable:
    """지정된 역할을 가진 사용자만 접근을 허용하는 의존성 팩토리."""

    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한이 부족합니다. 필요한 역할: {', '.join(roles)}",
            )
        return current_user

    return role_checker
