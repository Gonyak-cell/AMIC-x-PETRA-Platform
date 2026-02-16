from datetime import UTC, datetime

from fastapi import Request
from fastapi.responses import JSONResponse


class DARTAPIError(Exception):
    """DART API 호출 관련 오류"""

    def __init__(self, status_code: str, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class RateLimitExceededError(Exception):
    """Rate Limit 초과 오류"""

    def __init__(self, message: str = "Rate limit exceeded"):
        self.message = message
        super().__init__(message)


class ExternalAPIError(Exception):
    """외부 API 통신 오류"""

    def __init__(self, source: str, message: str):
        self.source = source
        self.message = message
        super().__init__(f"[{source}] {message}")


def _utc_timestamp() -> str:
    """현재 UTC 타임스탬프를 ISO 8601 형식으로 반환."""
    return datetime.now(UTC).isoformat()


async def dart_api_error_handler(request: Request, exc: DARTAPIError) -> JSONResponse:
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
    error_code = code_map.get(exc.status_code, "DART_UNKNOWN_ERROR")
    return JSONResponse(
        status_code=http_status,
        content={
            "detail": exc.message,
            "code": error_code,
            "timestamp": _utc_timestamp(),
            "dart_status": exc.status_code,
        },
    )


async def rate_limit_error_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": exc.message,
            "code": "RATE_LIMIT_EXCEEDED",
            "timestamp": _utc_timestamp(),
        },
    )


async def external_api_error_handler(request: Request, exc: ExternalAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": exc.message,
            "code": "EXTERNAL_API_ERROR",
            "timestamp": _utc_timestamp(),
            "source": exc.source,
        },
    )


def register_exception_handlers(app):
    app.add_exception_handler(DARTAPIError, dart_api_error_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_error_handler)
    app.add_exception_handler(ExternalAPIError, external_api_error_handler)
