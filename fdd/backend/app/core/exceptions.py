"""FDD 공통 예외 클래스 및 FastAPI 에러 핸들러.

마스터파일 §4.4 에러 처리 규칙 + §5.1 RFC 7807 (Problem Details) 형식.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import ErrorCode, ErrorSeverity, get_domain, get_severity

logger = logging.getLogger(__name__)


class FDDError(Exception):
    """FDD 도메인 에러 기본 클래스."""

    def __init__(
        self,
        code: ErrorCode,
        detail: str,
        *,
        severity: ErrorSeverity | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.severity = severity or get_severity(code)
        self.context = context or {}
        super().__init__(detail)

    def to_problem_detail(self) -> dict[str, Any]:
        """RFC 7807 Problem Details 형식으로 변환."""
        return {
            "type": f"urn:fdd:error:{get_domain(self.code)}:{self.code.value}",
            "title": self.code.name,
            "status": self._http_status(),
            "detail": self.detail,
            "code": self.code.value,
            "severity": self.severity.name,
            **({} if not self.context else {"context": self.context}),
        }

    def _http_status(self) -> int:
        if self.severity == ErrorSeverity.CRITICAL:
            return 500
        if self.code.value >= 9000:
            return 503
        return 422


class DataIntegrityError(FDDError):
    """데이터 무결성 위반 (tie-out 불일치, 금액 오차 등). CRITICAL."""

    def __init__(self, code: ErrorCode, detail: str, **kwargs: Any) -> None:
        super().__init__(code, detail, severity=ErrorSeverity.CRITICAL, **kwargs)


class ValidationError(FDDError):
    """입력 데이터 검증 실패."""

    def _http_status(self) -> int:
        return 400


class NotFoundError(FDDError):
    """리소스를 찾을 수 없음."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            ErrorCode.SYS_INTERNAL,
            f"{resource} not found: {resource_id}",
            severity=ErrorSeverity.ERROR,
        )

    def _http_status(self) -> int:
        return 404


class CalculationError(FDDError):
    """계산 엔진 오류 (QoE/NWC/Debt)."""


class AuthenticationError(FDDError):
    """인증 실패 (401 Unauthorized)."""

    def _http_status(self) -> int:
        return 401


class AuthorizationError(FDDError):
    """권한 부족 (403 Forbidden)."""

    def _http_status(self) -> int:
        return 403


# ──────────────────────────────────────────────
# FastAPI 에러 핸들러 등록
# ──────────────────────────────────────────────


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 FDD 에러 핸들러를 등록한다."""

    @app.exception_handler(FDDError)
    async def fdd_error_handler(request: Request, exc: FDDError) -> JSONResponse:
        body = exc.to_problem_detail()
        logger.error(
            "FDDError %s: %s",
            exc.code.name,
            exc.detail,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=body["status"],
            content=body,
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": "urn:fdd:error:system:9999",
                "title": "INTERNAL_ERROR",
                "status": 500,
                "detail": "An unexpected error occurred.",
                "code": 9999,
                "severity": "CRITICAL",
            },
            media_type="application/problem+json",
        )
