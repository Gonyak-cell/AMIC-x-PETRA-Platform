"""API 모듈 — FastAPI 앱 팩토리 및 공개 API.

> 마지막 수정: 2026-02-10 23:30:00

Auto-IM Generator REST API.
create_app() 팩토리 패턴으로 FastAPI 애플리케이션을 생성한다.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "create_app",
]

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


def _status_code_for(exc: APIError) -> int:
    """예외 타입에 따른 HTTP 상태 코드를 반환한다."""
    if isinstance(exc, AuthenticationError):
        return 401
    if isinstance(exc, AuthorizationError):
        return 403
    if isinstance(exc, NotFoundError):
        return 404
    if isinstance(exc, ConflictError):
        return 409
    if isinstance(exc, ValidationError):
        return 422
    return 500


async def _api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """APIError를 JSON 응답으로 변환한다."""
    return JSONResponse(
        status_code=_status_code_for(exc),
        content={"error": exc.message, "details": exc.details},
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """앱 시작/종료 시 리소스를 관리한다."""
    # startup: 필요 시 DB 엔진 초기화 등 수행
    yield
    # shutdown: 리소스 정리


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성하고 구성한다.

    Returns:
        구성된 FastAPI 인스턴스.
    """
    app = FastAPI(
        title="Auto-IM Generator API",
        description="M&A Information Memorandum 자동 생성 REST API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    # 미들웨어 등록 (순서: CORS → Rate Limit → Logging)
    _setup_middleware(app)

    # 예외 핸들러 등록
    app.add_exception_handler(APIError, _api_error_handler)  # type: ignore[arg-type]

    # 라우터 등록
    _include_routers(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    """미들웨어를 등록한다."""
    from src.api.middleware.cors import setup_cors
    from src.api.middleware.logging import setup_logging_middleware
    from src.api.middleware.rate_limit import setup_rate_limit

    setup_cors(app)
    setup_rate_limit(app)
    setup_logging_middleware(app)


def _include_routers(app: FastAPI) -> None:
    """라우터를 앱에 등록한다."""
    from src.api.routes.api_keys import router as api_keys_router
    from src.api.routes.auth import router as auth_router
    from src.api.routes.companies import router as companies_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.health import router as health_router
    from src.api.routes.users import router as users_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(documents_router)
    app.include_router(companies_router)
    app.include_router(api_keys_router)
