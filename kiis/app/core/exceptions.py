"""KIIS 예외 클래스 및 RFC 7807 Problem Details 핸들러."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import ErrorCode

logger = logging.getLogger(__name__)

# DART 상태 코드 → ErrorCode 자동 매핑
_DART_CODE_MAP: dict[str, ErrorCode] = {
    "010": ErrorCode.DART_AUTH_FAILED,
    "011": ErrorCode.DART_RATE_LIMITED,
    "013": ErrorCode.DART_NO_RESULT,
    "020": ErrorCode.DART_INVALID_PARAMS,
    "800": ErrorCode.DART_SYSTEM_MAINTENANCE,
}


class DARTAPIError(Exception):
    """DART API 호출 관련 오류"""

    def __init__(self, status_code: str, message: str):
        self.status_code = status_code
        self.message = message
        self.code = _DART_CODE_MAP.get(status_code)
        super().__init__(message)


class RateLimitExceededError(Exception):
    """Rate Limit 초과 오류"""

    def __init__(self, message: str = "Rate limit exceeded"):
        self.message = message
        self.code = ErrorCode.SYS_RATE_LIMIT
        super().__init__(message)


class ExternalAPIError(Exception):
    """외부 API 통신 오류"""

    def __init__(self, source: str, message: str):
        self.source = source
        self.message = message
        self.code = ErrorCode.SYS_EXTERNAL_API
        super().__init__(f"[{source}] {message}")


# ── RFC 7807 Problem Details ──────────────────────────────


def _problem_response(
    status: int,
    error_type: str,
    title: str,
    detail: str,
    *,
    error_code: ErrorCode | None = None,
    **extra: Any,
) -> JSONResponse:
    """RFC 7807 Problem Details JSON 응답을 생성한다."""
    body: dict[str, Any] = {
        "type": f"urn:kiis:error:{error_type}",
        "title": title,
        "status": status,
        "detail": detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if error_code is not None:
        body["error_code"] = f"KIIS-{error_code.value}"
    body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )


async def dart_api_error_handler(request: Request, exc: DARTAPIError) -> JSONResponse:
    logger.error("DARTAPIError [%s]: %s", exc.status_code, exc.message, exc_info=exc)
    status_map = {
        "010": 401,  # 미등록 키
        "011": 429,  # 사용 제한
        "013": 404,  # 결과 없음
        "020": 400,  # 파라미터 오류
        "800": 503,  # 시스템 점검
    }
    http_status = status_map.get(exc.status_code, 500)
    code_map = {
        "010": "DART_UNREGISTERED_KEY",
        "011": "DART_RATE_LIMITED",
        "013": "DART_NO_RESULT",
        "020": "DART_INVALID_PARAMS",
        "800": "DART_SYSTEM_MAINTENANCE",
    }
    error_title = code_map.get(exc.status_code, "DART_UNKNOWN_ERROR")
    return _problem_response(
        http_status,
        f"dart:{exc.status_code}",
        error_title,
        exc.message,
        error_code=exc.code,
        dart_status=exc.status_code,
    )


async def rate_limit_error_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return _problem_response(
        429,
        "system:rate_limit",
        "RATE_LIMIT_EXCEEDED",
        exc.message,
        error_code=exc.code,
    )


async def external_api_error_handler(request: Request, exc: ExternalAPIError) -> JSONResponse:
    logger.error("ExternalAPIError [%s]: %s", exc.source, exc.message, exc_info=exc)
    return _problem_response(
        502,
        f"external:{exc.source.lower()}",
        "EXTERNAL_API_ERROR",
        exc.message,
        error_code=exc.code,
        source=exc.source,
    )


def register_exception_handlers(app):
    app.add_exception_handler(DARTAPIError, dart_api_error_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_error_handler)
    app.add_exception_handler(ExternalAPIError, external_api_error_handler)
