"""Request logging 미들웨어 (T-I20).

> 마지막 수정: 2026-02-10 23:30:00

모든 요청의 method/path/status/duration을 로깅하며,
Authorization 헤더는 마스킹한다.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[..., Response],
    ) -> Response:
        """요청을 로깅하고 처리한다.

        Args:
            request: 요청 객체.
            call_next: 다음 미들웨어 또는 핸들러.

        Returns:
            응답 객체.
        """
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        # Authorization 헤더 마스킹
        auth_header = request.headers.get("authorization", "")
        masked_auth = "***MASKED***" if auth_header else ""

        logger.info(
            "Request: %s %s | Status: %d | Duration: %.2fms | Auth: %s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            masked_auth,
        )

        return response


def setup_logging_middleware(app: FastAPI) -> None:
    """Logging 미들웨어를 설정한다.

    Args:
        app: FastAPI 인스턴스.
    """
    app.add_middleware(RequestLoggingMiddleware)
