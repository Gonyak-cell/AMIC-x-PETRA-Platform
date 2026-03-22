from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Dev Auth"])

_DEV_AUTH_COOKIE = "dev_auth_email"
_DEV_AUTH_MAX_AGE = 60 * 60 * 12
_CREATED_AT = datetime(2025, 1, 1, tzinfo=UTC)

_DEV_ACCOUNTS = {
    "jwsuh@amic.kr": {
        "password": "1111",
        "user": {
            "id": "user-1",
            "email": "jwsuh@amic.kr",
            "display_name": "Jiwon Suh",
            "title": "Attorney",
            "role": "ADMIN",
            "is_active": True,
            "created_at": _CREATED_AT,
        },
    },
    "ytkim@amic.kr": {
        "password": "1111",
        "user": {
            "id": "user-2",
            "email": "ytkim@amic.kr",
            "display_name": "Yangtae Kim",
            "title": "CEO / CPA",
            "role": "ADMIN",
            "is_active": True,
            "created_at": _CREATED_AT,
        },
    },
    "yhlim@amic.kr": {
        "password": "1111",
        "user": {
            "id": "user-3",
            "email": "yhlim@amic.kr",
            "display_name": "Younghun Lim",
            "title": "Attorney",
            "role": "ANALYST",
            "is_active": True,
            "created_at": _CREATED_AT,
        },
    },
    "wsjo@amic.kr": {
        "password": "1111",
        "user": {
            "id": "user-4",
            "email": "wsjo@amic.kr",
            "display_name": "Woosang Jo",
            "title": "Director",
            "role": "ANALYST",
            "is_active": True,
            "created_at": _CREATED_AT,
        },
    },
    "bj.park@amic.kr": {
        "password": "1111",
        "user": {
            "id": "user-5",
            "email": "bj.park@amic.kr",
            "display_name": "Byungjoon Park",
            "title": "Attorney",
            "role": "ANALYST",
            "is_active": True,
            "created_at": _CREATED_AT,
        },
    },
    "tryoon@amic.kr": {
        "password": "1111",
        "user": {
            "id": "user-6",
            "email": "tryoon@amic.kr",
            "display_name": "Terry Yoon",
            "title": "Chief of Staff",
            "role": "ANALYST",
            "is_active": True,
            "created_at": _CREATED_AT,
        },
    },
}


class LoginRequest(BaseModel):
    email: str
    password: str


class MessageResponse(BaseModel):
    message: str


def _ensure_dev_auth_enabled() -> None:
    if settings.AUTH_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _set_dev_auth_cookie(response: Response, email: str) -> None:
    response.set_cookie(
        key=_DEV_AUTH_COOKIE,
        value=email,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=_DEV_AUTH_MAX_AGE,
        path="/",
    )


def _clear_dev_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=_DEV_AUTH_COOKIE, path="/")


def _get_current_user(request: Request) -> dict:
    email = request.cookies.get(_DEV_AUTH_COOKIE)
    account = _DEV_ACCOUNTS.get(email or "")
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return account["user"]


@router.post("/login", response_model=MessageResponse)
async def login(payload: LoginRequest, response: Response) -> MessageResponse:
    _ensure_dev_auth_enabled()
    account = _DEV_ACCOUNTS.get(payload.email)
    if not account or account["password"] != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    _set_dev_auth_cookie(response, payload.email)
    return MessageResponse(message="Login successful")


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    _ensure_dev_auth_enabled()
    _clear_dev_auth_cookie(response)
    return MessageResponse(message="Logged out")


@router.post("/refresh", response_model=MessageResponse)
async def refresh(request: Request) -> MessageResponse:
    _ensure_dev_auth_enabled()
    _get_current_user(request)
    return MessageResponse(message="Token refreshed")


@router.get("/me")
async def me(request: Request) -> dict:
    _ensure_dev_auth_enabled()
    return _get_current_user(request)


@router.get("/users")
async def list_users() -> list[dict]:
    _ensure_dev_auth_enabled()
    return [account["user"] for account in _DEV_ACCOUNTS.values()]


@router.post("/change-password", response_model=MessageResponse)
async def change_password() -> MessageResponse:
    _ensure_dev_auth_enabled()
    return MessageResponse(message="Password updated")
