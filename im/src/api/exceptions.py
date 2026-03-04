"""API 모듈 커스텀 예외 계층.

> 마지막 수정: 2026-02-10 16:29:08

FastAPI 엔드포인트에서 발생하는 예외를 정의한다.
모든 예외는 APIError를 상속하며, message + details 패턴을 따른다.
"""

from __future__ import annotations

from typing import Any

from src.api.core.errors import ErrorCode


class APIError(Exception):
    """API 모듈 최상위 예외."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        code: ErrorCode | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.code = code


# ============================================================================
# 인증/인가 예외
# ============================================================================


class AuthenticationError(APIError):
    """인증 실패 (유효하지 않은 토큰 또는 API 키)."""

    def __init__(
        self,
        message: str = "인증에 실패했습니다.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, details=details, code=ErrorCode.SYS_AUTH_FAILED
        )


class AuthorizationError(APIError):
    """인가 실패 (권한 부족)."""

    def __init__(
        self,
        message: str = "이 작업을 수행할 권한이 없습니다.",
        required_role: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            details={"required_role": required_role} if required_role else {},
            code=ErrorCode.SYS_AUTH_FORBIDDEN,
        )


# ============================================================================
# 리소스 예외
# ============================================================================


class NotFoundError(APIError):
    """요청한 리소스를 찾을 수 없음."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource_type} '{identifier}'을(를) 찾을 수 없습니다.",
            details={"resource_type": resource_type, "identifier": identifier},
            code=ErrorCode.DOC_NOT_FOUND,
        )


class ConflictError(APIError):
    """리소스 충돌 (이미 존재)."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource_type} '{identifier}'이(가) 이미 존재합니다.",
            details={"resource_type": resource_type, "identifier": identifier},
            code=ErrorCode.DOC_CONFLICT,
        )


# ============================================================================
# 태스크 예외
# ============================================================================


class TaskError(APIError):
    """비동기 태스크 실행 오류."""

    def __init__(
        self,
        message: str = "태스크 실행 중 오류가 발생했습니다.",
        task_id: str | None = None,
        stage: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            details={"task_id": task_id, "stage": stage},
            code=ErrorCode.TASK_EXECUTION_FAILED,
        )


# ============================================================================
# 유효성 검증 예외
# ============================================================================


class ValidationError(APIError):
    """입력 데이터 유효성 검증 실패."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(
            message=f"입력 검증 실패: 필드 '{field}' — {reason}",
            details={"field": field, "reason": reason},
            code=ErrorCode.VALIDATION_FIELD_ERROR,
        )
