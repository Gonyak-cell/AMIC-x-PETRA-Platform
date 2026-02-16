from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.auth import Token, TokenRefresh, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="사용자 등록")
async def register(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """새로운 사용자를 등록한다. username과 email은 고유해야 한다."""
    user = await service.register(db, user_create)
    return UserResponse.model_validate(user)


@router.post("/login", summary="로그인")
async def login(
    login_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """사용자명과 비밀번호로 로그인하여 JWT 토큰을 httpOnly 쿠키로 설정."""
    access_token, refresh_token = await service.login(db, login_data.username, login_data.password)

    # Access Token 쿠키 설정
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60,  # 15분
    )

    # Refresh Token 쿠키 설정
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7일
    )

    return {"message": "로그인 성공"}


@router.post("/refresh", summary="토큰 갱신")
async def refresh(
    token_refresh: TokenRefresh,
    response: Response,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """리프레시 토큰으로 새로운 액세스 토큰과 리프레시 토큰을 httpOnly 쿠키로 설정."""
    access_token, refresh_token = await service.refresh_token(db, token_refresh.refresh_token)

    # Access Token 쿠키 설정
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60,  # 15분
    )

    # Refresh Token 쿠키 설정
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7일
    )

    return {"message": "토큰 갱신 성공"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="로그아웃")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """현재 사용자를 로그아웃하고 쿠키를 삭제한다."""
    # 쿠키 삭제
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


@router.get("/me", response_model=UserResponse, summary="내 정보 조회")
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """현재 인증된 사용자의 정보를 조회한다."""
    return UserResponse.model_validate(current_user)
