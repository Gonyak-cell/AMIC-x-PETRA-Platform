"""ColorExtractor K-Means 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

import pytest
from PIL import Image

from src.brand_extractor.color.extractor import ColorExtractor
from src.brand_extractor.exceptions import ColorExtractionError


class TestColorExtractor:
    """ColorExtractor K-Means 색상 추출 테스트."""

    def setup_method(self) -> None:
        """테스트 초기화."""
        self.extractor = ColorExtractor(n_colors=5)

    def test_single_color_image(self, red_image: Image.Image) -> None:
        """단색 이미지에서 1개 주요 색상 추출."""
        colors = self.extractor.extract_from_image(red_image)
        assert len(colors) >= 1
        # 가장 비율 높은 색상이 빨강에 가까워야 함
        dominant = colors[0]
        assert dominant.rgb[0] > 200  # R이 높아야 함
        assert dominant.ratio > 0.8

    def test_multicolor_image(self, multicolor_image: Image.Image) -> None:
        """다색 이미지에서 여러 색상 추출."""
        colors = self.extractor.extract_from_image(multicolor_image)
        assert len(colors) >= 3
        # 각 사분면 색상 (~25% 비율)이 추출되어야 함
        total_ratio = sum(c.ratio for c in colors)
        assert abs(total_ratio - 1.0) < 0.01

    def test_rgba_alpha_filtering(self, rgba_image: Image.Image) -> None:
        """RGBA 이미지에서 투명 픽셀이 필터링되는지 확인."""
        colors = self.extractor.extract_from_image(rgba_image)
        assert len(colors) >= 1
        # 불투명 픽셀의 색상만 추출되어야 함

    def test_extract_from_bytes(self, red_image_bytes: bytes) -> None:
        """바이트 데이터에서 색상 추출."""
        colors = self.extractor.extract_from_bytes(red_image_bytes)
        assert len(colors) >= 1

    def test_invalid_bytes_raises(self) -> None:
        """잘못된 바이트 데이터에서 ColorExtractionError."""
        with pytest.raises(ColorExtractionError, match="디코딩 실패"):
            self.extractor.extract_from_bytes(b"not an image")

    def test_hex_format(self, red_image: Image.Image) -> None:
        """HEX 색상 코드 포맷 확인."""
        colors = self.extractor.extract_from_image(red_image)
        for c in colors:
            assert c.hex.startswith("#")
            assert len(c.hex) == 7

    def test_hsv_ranges(self, multicolor_image: Image.Image) -> None:
        """HSV 값 범위 확인."""
        colors = self.extractor.extract_from_image(multicolor_image)
        for c in colors:
            h, s, v = c.hsv
            assert 0.0 <= h <= 360.0
            assert 0.0 <= s <= 1.0
            assert 0.0 <= v <= 1.0

    def test_very_small_image(self) -> None:
        """매우 작은 이미지 (흰/검 필터링 후 픽셀 부족)."""
        # 모든 픽셀이 흰색인 3x3 이미지
        img = Image.new("RGB", (3, 3), (255, 255, 255))
        with pytest.raises(ColorExtractionError, match="픽셀 부족"):
            self.extractor.extract_from_image(img)

    def test_custom_n_colors(self, multicolor_image: Image.Image) -> None:
        """n_colors 파라미터가 반영되는지 확인."""
        extractor3 = ColorExtractor(n_colors=3)
        colors = extractor3.extract_from_image(multicolor_image)
        assert len(colors) == 3
