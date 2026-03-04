"""Data Ingestor 모듈 커스텀 예외 계층.

이 모듈은 DART API, 문서 파서, 웹 크롤러에서 발생하는 예외를 정의합니다.
"""

from __future__ import annotations

from typing import Any


class DataIngestorError(Exception):
    """Data Ingestor 모듈 최상위 예외."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ============================================================================
# DART API 예외
# ============================================================================


class DartAPIError(DataIngestorError):
    """DART API 관련 예외 기본 클래스."""

    pass


class DartAuthenticationError(DartAPIError):
    """DART API 인증 실패 (잘못된 API 키)."""

    def __init__(self, api_key_hint: str = "") -> None:
        super().__init__(
            message="DART API 인증 실패: API 키가 유효하지 않습니다.",
            details={"api_key_hint": api_key_hint},
        )


class DartRateLimitError(DartAPIError):
    """DART API 분당 호출 제한 초과 (100 calls/min)."""

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__(
            message="DART API 호출 제한 초과: 잠시 후 다시 시도하세요.",
            details={"retry_after_seconds": retry_after},
        )
        self.retry_after = retry_after


class DartNotFoundError(DartAPIError):
    """DART API에서 요청한 리소스를 찾을 수 없음."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(
            message=f"DART API: {resource_type} '{identifier}'을(를) 찾을 수 없습니다.",
            details={"resource_type": resource_type, "identifier": identifier},
        )


class DartResponseError(DartAPIError):
    """DART API 응답 파싱 또는 유효성 검증 실패."""

    def __init__(self, status_code: int, response_body: str | None = None) -> None:
        super().__init__(
            message=f"DART API 응답 오류: HTTP {status_code}",
            details={"status_code": status_code, "response_body": response_body},
        )
        self.status_code = status_code


class DartNetworkError(DartAPIError):
    """DART API 네트워크 연결 오류."""

    def __init__(self, original_error: Exception | None = None) -> None:
        super().__init__(
            message="DART API 네트워크 오류: 연결할 수 없습니다.",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


# ============================================================================
# 문서 파서 예외
# ============================================================================


class ParserError(DataIngestorError):
    """문서 파싱 관련 예외 기본 클래스."""

    pass


class PDFParserError(ParserError):
    """PDF 파싱 실패."""

    def __init__(self, file_path: str, reason: str = "") -> None:
        super().__init__(
            message=f"PDF 파싱 실패: {file_path}",
            details={"file_path": file_path, "reason": reason},
        )


class ExcelParserError(ParserError):
    """Excel 파싱 실패."""

    def __init__(
        self, file_path: str, sheet_name: str | None = None, reason: str = ""
    ) -> None:
        super().__init__(
            message=f"Excel 파싱 실패: {file_path}",
            details={
                "file_path": file_path,
                "sheet_name": sheet_name,
                "reason": reason,
            },
        )


class TableExtractionError(ParserError):
    """테이블 데이터 추출 실패."""

    def __init__(self, source: str, reason: str = "") -> None:
        super().__init__(
            message=f"테이블 추출 실패: {source}",
            details={"source": source, "reason": reason},
        )


class DataValidationError(ParserError):
    """추출된 데이터 유효성 검증 실패."""

    def __init__(self, field: str, expected: str, actual: Any) -> None:
        super().__init__(
            message=f"데이터 유효성 검증 실패: 필드 '{field}'",
            details={"field": field, "expected": expected, "actual": actual},
        )


# ============================================================================
# 웹 크롤러 예외
# ============================================================================


class CrawlerError(DataIngestorError):
    """웹 크롤링 관련 예외 기본 클래스."""

    pass


class CrawlerNetworkError(CrawlerError):
    """크롤링 네트워크 오류."""

    def __init__(self, url: str, original_error: Exception | None = None) -> None:
        super().__init__(
            message=f"크롤링 네트워크 오류: {url}",
            details={
                "url": url,
                "original_error": str(original_error) if original_error else None,
            },
        )
        self.url = url


class CrawlerTimeoutError(CrawlerError):
    """크롤링 타임아웃."""

    def __init__(self, url: str, timeout_seconds: float) -> None:
        super().__init__(
            message=f"크롤링 타임아웃: {url} ({timeout_seconds}초)",
            details={"url": url, "timeout_seconds": timeout_seconds},
        )


class CrawlerBlockedError(CrawlerError):
    """크롤링 차단됨 (robots.txt, IP 차단 등)."""

    def __init__(self, url: str, reason: str = "접근이 차단되었습니다.") -> None:
        super().__init__(
            message=f"크롤링 차단: {url}",
            details={"url": url, "reason": reason},
        )


class PageRenderError(CrawlerError):
    """JavaScript 페이지 렌더링 실패."""

    def __init__(self, url: str, reason: str = "") -> None:
        super().__init__(
            message=f"페이지 렌더링 실패: {url}",
            details={"url": url, "reason": reason},
        )


class ContentExtractionError(CrawlerError):
    """페이지 콘텐츠 추출 실패."""

    def __init__(self, url: str, selector: str | None = None, reason: str = "") -> None:
        super().__init__(
            message=f"콘텐츠 추출 실패: {url}",
            details={"url": url, "selector": selector, "reason": reason},
        )


# ============================================================================
# 집계/통합 예외
# ============================================================================


class AggregationError(DataIngestorError):
    """데이터 집계/통합 관련 예외."""

    pass


class MissingRequiredDataError(AggregationError):
    """필수 데이터 누락."""

    def __init__(self, missing_fields: list[str]) -> None:
        super().__init__(
            message=f"필수 데이터 누락: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields},
        )


class DataMergeConflictError(AggregationError):
    """데이터 병합 시 충돌 발생."""

    def __init__(self, field: str, values: list[Any]) -> None:
        super().__init__(
            message=f"데이터 병합 충돌: 필드 '{field}'에 여러 값 존재",
            details={"field": field, "conflicting_values": values},
        )


# ============================================================================
# 캐시 예외
# ============================================================================


class CacheError(DataIngestorError):
    """캐시 관련 예외."""

    pass


# ============================================================================
# 파이프라인 예외
# ============================================================================


class PipelineError(DataIngestorError):
    """파이프라인 관련 예외."""

    pass
