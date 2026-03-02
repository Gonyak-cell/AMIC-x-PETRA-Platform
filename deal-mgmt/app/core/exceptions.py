"""deal-mgmt 예외 클래스 및 RFC 7807 Problem Details 핸들러."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import ErrorCode

logger = logging.getLogger(__name__)


class ServiceUnavailableError(Exception):
    """외부 서비스 연결 실패 오류"""

    def __init__(self, service: str, message: str = ""):
        self.service = service
        self.message = message or f"{service} service is unavailable"
        self.code = ErrorCode.SYS_SERVICE_UNAVAILABLE
        super().__init__(self.message)


class WorkflowError(Exception):
    """워크플로우 상태 전환 오류"""

    def __init__(self, message: str, *, code: ErrorCode | None = None):
        self.message = message
        self.code = code or ErrorCode.WF_INVALID_TRANSITION
        super().__init__(message)


class ConflictError(Exception):
    """이해충돌 감지 오류"""

    def __init__(self, message: str):
        self.message = message
        self.code = ErrorCode.SYS_CONFLICT
        super().__init__(message)


class DocumentNotFoundError(Exception):
    """법률 문서 또는 트랜잭션 문서를 찾을 수 없는 오류."""

    def __init__(self, message: str = "문서를 찾을 수 없습니다."):
        self.message = message
        self.code = ErrorCode.DOC_NOT_FOUND
        super().__init__(message)


class DocumentNotReadyError(Exception):
    """문서가 아직 READY 상태가 아닌 오류."""

    def __init__(self, current_status: str):
        self.current_status = current_status
        self.message = f"문서가 아직 준비되지 않았습니다. 현재 상태: {current_status}"
        self.code = ErrorCode.DOC_NOT_READY
        super().__init__(self.message)


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
        "type": f"urn:deal-mgmt:error:{error_type}",
        "title": title,
        "status": status,
        "detail": detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if error_code is not None:
        body["error_code"] = f"MA-{error_code.value}"
    body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )


async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    logger.error("ServiceUnavailableError [%s]: %s", exc.service, exc.message, exc_info=exc)
    return _problem_response(
        502,
        "integration:service_unavailable",
        "SERVICE_UNAVAILABLE",
        exc.message,
        error_code=exc.code,
        service=exc.service,
    )


async def workflow_error_handler(request: Request, exc: WorkflowError) -> JSONResponse:
    logger.error("WorkflowError [%s %s]: %s", request.method, request.url.path, exc.message, exc_info=exc)
    return _problem_response(
        422,
        "workflow:transition_failed",
        "WORKFLOW_ERROR",
        exc.message,
        error_code=exc.code,
        instance=str(request.url.path),
    )


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return _problem_response(
        409,
        "domain:conflict",
        "CONFLICT_ERROR",
        exc.message,
        error_code=exc.code,
    )


async def document_not_found_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
    return _problem_response(
        404,
        "document:not_found",
        "DOCUMENT_NOT_FOUND",
        exc.message,
        error_code=exc.code,
    )


async def document_not_ready_handler(request: Request, exc: DocumentNotReadyError) -> JSONResponse:
    return _problem_response(
        400,
        "document:not_ready",
        "DOCUMENT_NOT_READY",
        exc.message,
        error_code=exc.code,
        current_status=exc.current_status,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
    app.add_exception_handler(WorkflowError, workflow_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(DocumentNotFoundError, document_not_found_handler)
    app.add_exception_handler(DocumentNotReadyError, document_not_ready_handler)
