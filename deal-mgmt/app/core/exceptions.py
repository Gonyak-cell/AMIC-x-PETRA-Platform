from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ServiceUnavailableError(Exception):
    """외부 서비스 연결 실패 오류"""

    def __init__(self, service: str, message: str = ""):
        self.service = service
        self.message = message or f"{service} service is unavailable"
        super().__init__(self.message)


class WorkflowError(Exception):
    """워크플로우 상태 전환 오류"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ConflictError(Exception):
    """이해충돌 감지 오류"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": exc.message,
            "code": "SERVICE_UNAVAILABLE",
            "timestamp": _utc_timestamp(),
            "service": exc.service,
        },
    )


async def workflow_error_handler(request: Request, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.message,
            "code": "WORKFLOW_ERROR",
            "timestamp": _utc_timestamp(),
        },
    )


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": exc.message,
            "code": "CONFLICT_ERROR",
            "timestamp": _utc_timestamp(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
    app.add_exception_handler(WorkflowError, workflow_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
