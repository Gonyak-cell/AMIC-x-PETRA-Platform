"""Industry 모듈 커스텀 예외 계층.

> 마지막 수정: 2026-02-11 10:00:00

산업 모듈 조회, 설정, 검증에서 발생하는 예외를 정의합니다.
"""

from __future__ import annotations

from typing import Any


class IndustryError(Exception):
    """Industry 모듈 최상위 예외."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnsupportedIndustryError(IndustryError):
    """미등록 또는 미지원 산업 식별자."""

    def __init__(
        self,
        industry_id: str,
        available: list[str] | None = None,
    ) -> None:
        super().__init__(
            message=(
                f"미지원 산업: '{industry_id}'. "
                f"지원 산업: {available or []}"
            ),
            details={
                "industry_id": industry_id,
                "available": available or [],
            },
        )
        self.industry_id = industry_id
