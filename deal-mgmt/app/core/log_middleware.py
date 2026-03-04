"""통합 요청/응답 로깅 미들웨어.

모든 요청에 X-Request-ID를 할당하고, HTTP 정보를 JSON 구조화 로그로 기록한다.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.log_context import set_request_id, set_user_id

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """JSON 구조화 요청/응답 로깅 미들웨어."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:  # type: ignore[override]
        # 1. Request ID 설정 (X-Request-ID 헤더 또는 자동 생성)
        request_id = set_request_id(request.headers.get("x-request-id"))

        # 2. 인증된 사용자 ID (있으면 — auth 미들웨어가 먼저 실행된 경우)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            set_user_id(str(user_id))

        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # 3. 응답 헤더에 request_id 추가
        response.headers["X-Request-ID"] = request_id

        # 4. HTTP 로그 출력 (extra={"http": {...}}로 JSONFormatter가 처리)
        logger.info(
            "HTTP %s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "http": {
                    "method": request.method,
                    "path": str(request.url.path),
                    "query": str(request.url.query) if request.url.query else None,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                    "user_id": str(user_id) if user_id else None,
                }
            },
        )

        return response


def setup_request_logging(app: FastAPI) -> None:
    """요청 로깅 미들웨어를 등록한다."""
    app.add_middleware(RequestLoggingMiddleware)
