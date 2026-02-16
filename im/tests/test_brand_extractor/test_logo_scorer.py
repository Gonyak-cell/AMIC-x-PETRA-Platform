"""LogoScorer 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from src.brand_extractor.config import BrandExtractorConfig
from src.brand_extractor.logo.scorer import LogoScorer
from src.brand_extractor.models import LogoCandidate


class TestLogoScorer:
    """LogoScorer 품질 스코어링 테스트."""

    def setup_method(self) -> None:
        """테스트 초기화."""
        config = BrandExtractorConfig(
            min_logo_size=64,
            preferred_logo_size=512,
        )
        self.scorer = LogoScorer(config)

    def test_high_res_png_scores_higher(self) -> None:
        """고해상도 PNG가 저해상도 JPEG보다 높은 점수."""
        score_png = self.scorer._calculate_score(
            width=512, height=512, has_transparency=True, fmt="png", source="apple-touch-icon"
        )
        score_jpeg = self.scorer._calculate_score(
            width=100, height=100, has_transparency=False, fmt="jpeg", source="favicon"
        )
        assert score_png > score_jpeg

    def test_below_min_size_gets_zero_resolution(self) -> None:
        """최소 크기 미달 시 해상도 점수 0."""
        score = self.scorer._calculate_score(
            width=32, height=32, has_transparency=False, fmt="ico", source="favicon"
        )
        # 해상도 0이므로 전체 점수가 낮아야 함
        assert score < 0.5

    def test_svg_gets_high_format_score(self) -> None:
        """SVG 포맷이 높은 점수를 받는지 확인."""
        score_svg = self.scorer._calculate_score(
            width=512, height=512, has_transparency=True, fmt="svg", source="apple-touch-icon"
        )
        score_png = self.scorer._calculate_score(
            width=512, height=512, has_transparency=True, fmt="png", source="apple-touch-icon"
        )
        assert score_svg > score_png

    def test_score_range_0_to_1(self) -> None:
        """점수가 0-1 범위인지 확인."""
        score = self.scorer._calculate_score(
            width=1024, height=1024, has_transparency=True, fmt="svg", source="apple-touch-icon"
        )
        assert 0.0 <= score <= 1.0

        score_low = self.scorer._calculate_score(
            width=0, height=0, has_transparency=False, fmt="", source=""
        )
        assert 0.0 <= score_low <= 1.0

    def test_square_ratio_preferred(self) -> None:
        """정사각형 이미지가 극단적 비율보다 높은 점수."""
        score_square = self.scorer._calculate_score(
            width=256, height=256, has_transparency=True, fmt="png", source="og:image"
        )
        score_wide = self.scorer._calculate_score(
            width=1200, height=100, has_transparency=True, fmt="png", source="og:image"
        )
        assert score_square > score_wide
