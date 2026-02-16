"""Data Ingestor 예외 클래스 테스트.

T-D01 검증: 예외 클래스 임포트 및 인스턴스화 테스트
"""

import pytest

from src.data_ingestor import (
    AggregationError,
    ContentExtractionError,
    CrawlerBlockedError,
    CrawlerError,
    CrawlerNetworkError,
    CrawlerTimeoutError,
    DartAPIError,
    DartAuthenticationError,
    DartNetworkError,
    DartNotFoundError,
    DartRateLimitError,
    DartResponseError,
    DataIngestorError,
    DataMergeConflictError,
    DataValidationError,
    ExcelParserError,
    MissingRequiredDataError,
    PageRenderError,
    ParserError,
    PDFParserError,
    TableExtractionError,
)


class TestExceptionHierarchy:
    """예외 계층 구조 테스트."""

    def test_base_exception(self) -> None:
        """DataIngestorError 기본 예외 테스트."""
        error = DataIngestorError("테스트 오류", {"key": "value"})
        assert str(error) == "테스트 오류"
        assert error.message == "테스트 오류"
        assert error.details == {"key": "value"}

    def test_base_exception_without_details(self) -> None:
        """DataIngestorError details 없이 생성."""
        error = DataIngestorError("테스트 오류")
        assert error.details == {}


class TestDartAPIErrors:
    """DART API 예외 테스트."""

    def test_dart_api_error_inheritance(self) -> None:
        """DartAPIError 상속 확인."""
        error = DartAPIError("DART 오류")
        assert isinstance(error, DataIngestorError)

    def test_dart_authentication_error(self) -> None:
        """DartAuthenticationError 테스트."""
        error = DartAuthenticationError(api_key_hint="abc***")
        assert "인증 실패" in error.message
        assert error.details["api_key_hint"] == "abc***"
        assert isinstance(error, DartAPIError)

    def test_dart_rate_limit_error(self) -> None:
        """DartRateLimitError 테스트."""
        error = DartRateLimitError(retry_after=30.0)
        assert "호출 제한 초과" in error.message
        assert error.retry_after == 30.0
        assert error.details["retry_after_seconds"] == 30.0

    def test_dart_not_found_error(self) -> None:
        """DartNotFoundError 테스트."""
        error = DartNotFoundError(resource_type="기업", identifier="00123456")
        assert "찾을 수 없습니다" in error.message
        assert error.details["resource_type"] == "기업"
        assert error.details["identifier"] == "00123456"

    def test_dart_response_error(self) -> None:
        """DartResponseError 테스트."""
        error = DartResponseError(status_code=400, response_body='{"error": "bad request"}')
        assert "HTTP 400" in error.message
        assert error.status_code == 400
        assert error.details["response_body"] == '{"error": "bad request"}'

    def test_dart_network_error(self) -> None:
        """DartNetworkError 테스트."""
        original = ConnectionError("Connection refused")
        error = DartNetworkError(original_error=original)
        assert "네트워크 오류" in error.message
        assert error.original_error == original
        assert "Connection refused" in error.details["original_error"]


class TestParserErrors:
    """파서 예외 테스트."""

    def test_parser_error_inheritance(self) -> None:
        """ParserError 상속 확인."""
        error = ParserError("파싱 오류")
        assert isinstance(error, DataIngestorError)

    def test_pdf_parser_error(self) -> None:
        """PDFParserError 테스트."""
        error = PDFParserError(file_path="/path/to/file.pdf", reason="암호화됨")
        assert "PDF 파싱 실패" in error.message
        assert error.details["file_path"] == "/path/to/file.pdf"
        assert error.details["reason"] == "암호화됨"

    def test_excel_parser_error(self) -> None:
        """ExcelParserError 테스트."""
        error = ExcelParserError(
            file_path="/path/to/file.xlsx",
            sheet_name="Sheet1",
            reason="형식 오류",
        )
        assert "Excel 파싱 실패" in error.message
        assert error.details["sheet_name"] == "Sheet1"

    def test_table_extraction_error(self) -> None:
        """TableExtractionError 테스트."""
        error = TableExtractionError(source="page 1", reason="테이블 없음")
        assert "테이블 추출 실패" in error.message

    def test_data_validation_error(self) -> None:
        """DataValidationError 테스트."""
        error = DataValidationError(field="revenue", expected="숫자", actual="N/A")
        assert "유효성 검증 실패" in error.message
        assert error.details["expected"] == "숫자"
        assert error.details["actual"] == "N/A"


class TestCrawlerErrors:
    """크롤러 예외 테스트."""

    def test_crawler_error_inheritance(self) -> None:
        """CrawlerError 상속 확인."""
        error = CrawlerError("크롤링 오류")
        assert isinstance(error, DataIngestorError)

    def test_crawler_network_error(self) -> None:
        """CrawlerNetworkError 테스트."""
        error = CrawlerNetworkError(url="https://example.com", original_error=TimeoutError())
        assert "네트워크 오류" in error.message
        assert error.url == "https://example.com"

    def test_crawler_timeout_error(self) -> None:
        """CrawlerTimeoutError 테스트."""
        error = CrawlerTimeoutError(url="https://example.com", timeout_seconds=30.0)
        assert "타임아웃" in error.message
        assert error.details["timeout_seconds"] == 30.0

    def test_crawler_blocked_error(self) -> None:
        """CrawlerBlockedError 테스트."""
        error = CrawlerBlockedError(url="https://example.com", reason="robots.txt 차단")
        assert "차단" in error.message
        assert error.details["reason"] == "robots.txt 차단"

    def test_page_render_error(self) -> None:
        """PageRenderError 테스트."""
        error = PageRenderError(url="https://example.com", reason="JavaScript 오류")
        assert "렌더링 실패" in error.message

    def test_content_extraction_error(self) -> None:
        """ContentExtractionError 테스트."""
        error = ContentExtractionError(
            url="https://example.com",
            selector="div.content",
            reason="요소 없음",
        )
        assert "콘텐츠 추출 실패" in error.message
        assert error.details["selector"] == "div.content"


class TestAggregationErrors:
    """집계 예외 테스트."""

    def test_aggregation_error_inheritance(self) -> None:
        """AggregationError 상속 확인."""
        error = AggregationError("집계 오류")
        assert isinstance(error, DataIngestorError)

    def test_missing_required_data_error(self) -> None:
        """MissingRequiredDataError 테스트."""
        error = MissingRequiredDataError(missing_fields=["revenue", "net_income"])
        assert "필수 데이터 누락" in error.message
        assert "revenue" in error.details["missing_fields"]
        assert "net_income" in error.details["missing_fields"]

    def test_data_merge_conflict_error(self) -> None:
        """DataMergeConflictError 테스트."""
        error = DataMergeConflictError(field="revenue", values=[100, 150])
        assert "병합 충돌" in error.message
        assert error.details["conflicting_values"] == [100, 150]


class TestExceptionRaising:
    """예외 발생 및 캐치 테스트."""

    def test_catch_specific_exception(self) -> None:
        """특정 예외 캐치."""
        with pytest.raises(DartRateLimitError) as exc_info:
            raise DartRateLimitError(retry_after=60.0)

        assert exc_info.value.retry_after == 60.0

    def test_catch_parent_exception(self) -> None:
        """부모 예외로 캐치."""
        with pytest.raises(DartAPIError):
            raise DartAuthenticationError()

    def test_catch_base_exception(self) -> None:
        """기본 예외로 캐치."""
        with pytest.raises(DataIngestorError):
            raise CrawlerTimeoutError(url="https://example.com", timeout_seconds=30.0)
