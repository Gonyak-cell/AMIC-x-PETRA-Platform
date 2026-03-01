"""크롤러 테스트."""

from __future__ import annotations

from datetime import datetime


from src.data_ingestor.crawler.company_crawler import CompanyCrawler, CompanyWebInfo, IRDocument
from src.data_ingestor.crawler.news_crawler import NewsArticle, NewsCrawler
from src.data_ingestor.crawler.playwright_engine import CrawlerConfig, PageResult, PlaywrightEngine


class TestCrawlerConfig:
    """CrawlerConfig 테스트."""

    def test_default_values(self) -> None:
        """기본값 테스트."""
        config = CrawlerConfig()

        assert config.headless is True
        assert config.timeout == 30.0
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.locale == "ko-KR"

    def test_custom_values(self) -> None:
        """커스텀 값 테스트."""
        config = CrawlerConfig(
            headless=False,
            timeout=60.0,
            block_images=True,
        )

        assert config.headless is False
        assert config.timeout == 60.0
        assert config.block_images is True


class TestPageResult:
    """PageResult 테스트."""

    def test_page_result_creation(self) -> None:
        """페이지 결과 생성 테스트."""
        result = PageResult(
            url="https://example.com",
            html="<html></html>",
            title="Example",
            status=200,
            load_time_ms=150.5,
        )

        assert result.url == "https://example.com"
        assert result.status == 200
        assert result.load_time_ms == 150.5


class TestPlaywrightEngine:
    """PlaywrightEngine 테스트."""

    def test_init_default_config(self) -> None:
        """기본 설정 초기화 테스트."""
        engine = PlaywrightEngine()

        assert engine.config.headless is True
        assert engine._browser is None
        assert engine.is_connected is False

    def test_init_custom_config(self) -> None:
        """커스텀 설정 초기화 테스트."""
        config = CrawlerConfig(headless=False, timeout=60.0)
        engine = PlaywrightEngine(config)

        assert engine.config.headless is False
        assert engine.config.timeout == 60.0


class TestNewsArticle:
    """NewsArticle 테스트."""

    def test_to_dict(self) -> None:
        """딕셔너리 변환 테스트."""
        article = NewsArticle(
            title="테스트 기사",
            url="https://news.example.com/article",
            source="테스트 뉴스",
            published_at=datetime(2024, 1, 15),
            summary="기사 요약",
        )

        result = article.to_dict()

        assert result["title"] == "테스트 기사"
        assert result["source"] == "테스트 뉴스"
        assert "2024-01-15" in result["published_at"]


class TestNewsCrawler:
    """NewsCrawler 테스트."""

    def test_init_default_values(self) -> None:
        """기본값 초기화 테스트."""
        crawler = NewsCrawler()

        assert crawler._config.headless is True
        assert crawler._config.timeout == 30.0

    def test_init_custom_values(self) -> None:
        """커스텀 값 초기화 테스트."""
        crawler = NewsCrawler(headless=False, timeout=60.0)

        assert crawler._config.headless is False
        assert crawler._config.timeout == 60.0

    def test_parse_naver_date_relative(self) -> None:
        """네이버 상대 날짜 파싱 테스트."""
        crawler = NewsCrawler()

        # "1시간 전"
        result = crawler._parse_naver_date("1시간 전")
        assert result is not None
        assert (datetime.now() - result).seconds < 7200  # 2시간 이내

        # "3일 전"
        result = crawler._parse_naver_date("3일 전")
        assert result is not None

    def test_parse_naver_date_absolute(self) -> None:
        """네이버 절대 날짜 파싱 테스트."""
        crawler = NewsCrawler()

        result = crawler._parse_naver_date("2024.01.15.")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_clean_article_text(self) -> None:
        """기사 본문 정리 테스트."""
        crawler = NewsCrawler()

        text = "기사 내용입니다.   많은 공백이 있습니다.   [홍길동 기자]"
        result = crawler._clean_article_text(text)

        assert "기사 내용입니다" in result
        assert "[홍길동 기자]" not in result
        assert "   " not in result  # 연속 공백 제거


class TestCompanyWebInfo:
    """CompanyWebInfo 테스트."""

    def test_to_dict(self) -> None:
        """딕셔너리 변환 테스트."""
        info = CompanyWebInfo(
            url="https://example.com",
            name="테스트 회사",
            description="회사 설명",
            ir_url="https://example.com/ir",
        )

        result = info.to_dict()

        assert result["name"] == "테스트 회사"
        assert result["ir_url"] == "https://example.com/ir"


class TestIRDocument:
    """IRDocument 테스트."""

    def test_creation(self) -> None:
        """생성 테스트."""
        doc = IRDocument(
            title="2024년 사업보고서",
            url="https://example.com/report.pdf",
            doc_type="annual_report",
            file_type="pdf",
        )

        assert doc.title == "2024년 사업보고서"
        assert doc.doc_type == "annual_report"
        assert doc.file_type == "pdf"


class TestCompanyCrawler:
    """CompanyCrawler 테스트."""

    def test_init_default_values(self) -> None:
        """기본값 초기화 테스트."""
        crawler = CompanyCrawler()

        assert crawler._config.headless is True
        assert crawler._config.timeout == 30.0

    def test_find_page_url(self) -> None:
        """페이지 URL 찾기 테스트."""
        crawler = CompanyCrawler()

        links = [
            {"href": "https://example.com/about", "text": "회사소개"},
            {"href": "https://example.com/ir", "text": "투자정보"},
            {"href": "https://example.com/careers", "text": "채용"},
        ]

        # About 페이지 찾기
        result = crawler._find_page_url(links, crawler.ABOUT_PATTERNS, "https://example.com")
        assert "/about" in result

        # IR 페이지 찾기
        result = crawler._find_page_url(links, crawler.IR_PATTERNS, "https://example.com")
        assert "/ir" in result

        # 없는 패턴
        result = crawler._find_page_url(links, ["/nonexistent"], "https://example.com")
        assert result == ""
