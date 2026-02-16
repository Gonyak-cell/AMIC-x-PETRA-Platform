"""Rate limiting 미들웨어 (T-I20).

> 마지막 수정: 2026-02-10 23:30:00

SlowAPI 기반 분당 요청 제한.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    """Rate limit 키를 반환한다 (IP 주소 기반).

    Args:
        request: FastAPI 요청 객체.

    Returns:
        클라이언트 IP 주소 문자열.
    """
    return get_remote_address(request)


def setup_rate_limit(app: FastAPI) -> None:
    """Rate limiting 미들웨어를 설정한다.

    Args:
        app: FastAPI 인스턴스.
    """
    from src.api.config import get_config

    config = get_config()

    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=[f"{config.rate_limit_per_minute}/minute"],
        storage_uri=config.redis_url,
    )

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
