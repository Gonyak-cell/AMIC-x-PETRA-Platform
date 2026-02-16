"""BrandAssets / LogoCandidate / ExtractedColor 모델 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from src.brand_extractor.models import BrandAssets, ExtractedColor, LogoCandidate


class TestBrandAssets:
    """BrandAssets 데이터클래스 테스트."""

    def test_defaults_are_amic(self) -> None:
        """기본값이 AMIC 컬러인지 확인."""
        brand = BrandAssets()
        assert brand.primary_color == "#0F3A32"
        assert brand.secondary_color == "#26C260"
        assert brand.confidence == 0.0
        assert brand.source == "fallback"

    def test_custom_values(self) -> None:
        """사용자 정의 값 설정 확인."""
        brand = BrandAssets(
            company_name="테스트",
            primary_color="#FF0000",
            secondary_color="#00FF00",
            confidence=0.9,
            source="brandfetch",
        )
        assert brand.company_name == "테스트"
        assert brand.primary_color == "#FF0000"
        assert brand.confidence == 0.9

    def test_warnings_and_additional_colors(self) -> None:
        """warnings, additional_colors 리스트 기본값 확인."""
        brand = BrandAssets()
        assert brand.warnings == []
        assert brand.additional_colors == []
        brand.warnings.append("test warning")
        assert len(brand.warnings) == 1


class TestLogoCandidate:
    """LogoCandidate 데이터클래스 테스트."""

    def test_required_fields(self) -> None:
        """필수 필드 확인."""
        candidate = LogoCandidate(url="https://example.com/logo.png", source="og:image")
        assert candidate.url == "https://example.com/logo.png"
        assert candidate.source == "og:image"
        assert candidate.score == 0.0

    def test_default_values(self) -> None:
        """기본값 확인."""
        candidate = LogoCandidate(url="test", source="favicon")
        assert candidate.width == 0
        assert candidate.height == 0
        assert candidate.has_transparency is False
        assert candidate.format == ""


class TestExtractedColor:
    """ExtractedColor 데이터클래스 테스트."""

    def test_hsv_values(self) -> None:
        """HSV 값 범위 확인."""
        color = ExtractedColor(
            hex="#FF0000",
            rgb=(255, 0, 0),
            hsv=(0.0, 1.0, 1.0),
            ratio=0.5,
        )
        assert color.hsv[0] == 0.0  # Hue
        assert color.hsv[1] == 1.0  # Saturation
        assert color.hsv[2] == 1.0  # Value
        assert color.role == ""

    def test_role_assignment(self) -> None:
        """role 할당 확인."""
        color = ExtractedColor(
            hex="#0000FF",
            rgb=(0, 0, 255),
            hsv=(240.0, 1.0, 1.0),
            ratio=0.3,
            role="primary",
        )
        assert color.role == "primary"
