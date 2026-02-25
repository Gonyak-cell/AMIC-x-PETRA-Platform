from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """사용자 등록 요청"""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """사용자 로그인 요청"""

    username: str
    password: str


class Token(BaseModel):
    """JWT 토큰 응답"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """토큰 갱신 요청"""

    refresh_token: str


class UserResponse(BaseModel):
    """사용자 정보 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    title: str = ""
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None
