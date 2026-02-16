"""ColorClassifier 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

from src.brand_extractor.color.classifier import ColorClassifier
from src.brand_extractor.models import ExtractedColor


class TestColorClassifier:
    """ColorClassifier 색상 분류 테스트."""

    def setup_method(self) -> None:
        """테스트 초기화."""
        self.classifier = ColorClassifier()

    def test_primary_secondary_classification(
        self, sample_extracted_colors: list[ExtractedColor]
    ) -> None:
        """유채색에서 Primary/Secondary 분류."""
        classified = self.classifier.classify(sample_extracted_colors)
        roles = {c.role for c in classified if c.role}
        assert "primary" in roles

    def test_achromatic_only_fallback(self) -> None:
        """모든 색상이 무채색일 때 비율 최대를 primary로."""
        colors = [
            ExtractedColor(hex="#808080", rgb=(128, 128, 128), hsv=(0.0, 0.0, 0.502), ratio=0.5),
            ExtractedColor(hex="#404040", rgb=(64, 64, 64), hsv=(0.0, 0.0, 0.251), ratio=0.3),
            ExtractedColor(hex="#C0C0C0", rgb=(192, 192, 192), hsv=(0.0, 0.0, 0.753), ratio=0.2),
        ]
        classified = self.classifier.classify(colors)
        primary = [c for c in classified if c.role == "primary"]
        assert len(primary) == 1
        assert primary[0].hex == "#808080"  # 가장 높은 비율

    def test_hue_distance_requirement(self) -> None:
        """Primary와 색상환 거리가 가까운 색은 secondary가 되지 않음."""
        colors = [
            ExtractedColor(hex="#FF0000", rgb=(255, 0, 0), hsv=(0.0, 1.0, 1.0), ratio=0.5),
            ExtractedColor(hex="#FF3300", rgb=(255, 51, 0), hsv=(12.0, 1.0, 1.0), ratio=0.3),
            ExtractedColor(hex="#0000FF", rgb=(0, 0, 255), hsv=(240.0, 1.0, 1.0), ratio=0.2),
        ]
        classified = self.classifier.classify(colors)
        primary = [c for c in classified if c.role == "primary"]
        secondary = [c for c in classified if c.role == "secondary"]
        assert len(primary) == 1
        assert primary[0].hex == "#FF0000"
        # FF3300은 12°로 거리가 30° 미만이므로 secondary가 아님
        # 0000FF (240°)가 secondary가 되어야 함
        assert len(secondary) == 1
        assert secondary[0].hex == "#0000FF"

    def test_empty_colors(self) -> None:
        """빈 리스트에서 빈 결과."""
        assert self.classifier.classify([]) == []

    def test_single_chromatic_color(self) -> None:
        """유채색 1개만 있을 때 primary 할당."""
        colors = [
            ExtractedColor(hex="#FF0000", rgb=(255, 0, 0), hsv=(0.0, 1.0, 1.0), ratio=1.0),
        ]
        classified = self.classifier.classify(colors)
        assert classified[0].role == "primary"

    def test_hue_distance_calculation(self) -> None:
        """색상환 거리 계산 검증."""
        assert ColorClassifier._hue_distance(0.0, 180.0) == 180.0
        assert ColorClassifier._hue_distance(350.0, 10.0) == 20.0
        assert ColorClassifier._hue_distance(90.0, 90.0) == 0.0

    def test_achromatic_detection(self) -> None:
        """무채색 판별 검증."""
        achromatic = ExtractedColor(
            hex="#808080", rgb=(128, 128, 128), hsv=(0.0, 0.0, 0.502), ratio=0.5
        )
        chromatic = ExtractedColor(
            hex="#FF0000", rgb=(255, 0, 0), hsv=(0.0, 1.0, 1.0), ratio=0.5
        )
        assert ColorClassifier._is_achromatic(achromatic) is True
        assert ColorClassifier._is_achromatic(chromatic) is False
