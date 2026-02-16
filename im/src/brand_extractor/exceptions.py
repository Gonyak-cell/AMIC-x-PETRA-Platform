"""Brand Extractor 예외 계층 (T-B01).

> 마지막 수정: 2026-02-10 22:00:00

BrandExtractorError를 기반으로 Brandfetch, 로고, 색상, 웹사이트 도메인별
세분화된 예외를 제공한다.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class BrandExtractorError(Exception):
    """Brand Extractor 모듈 최상위 예외.

    Attributes:
        message: 사람이 읽을 수 있는 오류 메시지.
        details: 프로그래밍 방식 접근을 위한 구조화된 컨텍스트.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Brandfetch API
# ---------------------------------------------------------------------------


class BrandfetchAPIError(BrandExtractorError):
    """Brandfetch API 호출 실패."""

    def __init__(self, status_code: int = 0, original_error: str = "") -> None:
        super().__init__(
            message=f"Brandfetch API 오류: status={status_code} — {original_error}",
            details={"status_code": status_code, "original_error": original_error},
        )


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------


class LogoDetectionError(BrandExtractorError):
    """로고 탐지/처리 실패."""

    def __init__(self, url: str = "", reason: str = "") -> None:
        super().__init__(
            message=f"로고 탐지 실패: url='{url}' — {reason}",
            details={"url": url, "reason": reason},
        )


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------


class ColorExtractionError(BrandExtractorError):
    """색상 추출 실패."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(
            message=f"색상 추출 실패: {reason}",
            details={"reason": reason},
        )


# ---------------------------------------------------------------------------
# Website
# ---------------------------------------------------------------------------


class WebsiteAccessError(BrandExtractorError):
    """웹사이트 접근 실패."""

    def __init__(self, url: str = "", original_error: str = "") -> None:
        super().__init__(
            message=f"웹사이트 접근 실패: url='{url}' — {original_error}",
            details={"url": url, "original_error": original_error},
        )
