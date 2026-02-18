from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

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


async def get_jwt_claims(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> JWTClaims:
    """JWT 토큰에서 클레임만 추출한다 (DB 조회 없음).

    FDD가 발급한 JWT를 디코딩하여 user_id, email, role을 반환한다.
    deal-mgmt는 자체 User DB가 없으므로 클레임만 사용한다.
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


def require_role(*roles: str):
    """지정된 역할을 가진 사용자만 접근을 허용하는 의존성 팩토리."""

    async def role_checker(
        claims: JWTClaims = Depends(get_jwt_claims),
    ) -> JWTClaims:
        if claims.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한이 부족합니다. 필요한 역할: {', '.join(roles)}",
            )
        return claims

    return role_checker
