"""FallbackExtractor 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from src.brand_extractor.extractors.fallback import FallbackExtractor


class TestFallbackExtractor:
    """FallbackExtractor AMIC 폴백 테스트."""

    def setup_method(self) -> None:
        """테스트 초기화."""
        self.extractor = FallbackExtractor()

    def test_amic_defaults(self) -> None:
        """AMIC 기본 색상/로고 반환."""
        brand = self.extractor.extract()
        assert brand.primary_color == "#0F3A32"
        assert brand.secondary_color == "#26C260"
        assert brand.logo_dark_path == "amic_logo_dark.png"
        assert brand.logo_white_path == "amic_logo_white.png"
        assert brand.cover_bg_path == "amic_cover_bg.jpeg"

    def test_confidence_zero(self) -> None:
        """confidence가 0.0."""
        brand = self.extractor.extract()
        assert brand.confidence == 0.0

    def test_source_fallback(self) -> None:
        """source가 'fallback'."""
        brand = self.extractor.extract()
        assert brand.source == "fallback"

    def test_company_name_passed(self) -> None:
        """company_name이 전달되는지 확인."""
        brand = self.extractor.extract(company_name="삼성전자")
        assert brand.company_name == "삼성전자"

    def test_empty_company_name(self) -> None:
        """company_name 미전달 시 빈값."""
        brand = self.extractor.extract()
        assert brand.company_name == ""
