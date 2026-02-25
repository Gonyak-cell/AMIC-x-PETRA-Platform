"""CORS 미들웨어 (T-I20).

> 마지막 수정: 2026-02-10 23:30:00

명시적 오리진 리스트 기반 CORS (와일드카드 금지).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """CORS 미들웨어를 설정한다.

    Args:
        app: FastAPI 인스턴스.
    """
    from src.api.config import get_config

    config = get_config()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        max_age=3600,
    )
