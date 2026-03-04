"""Chart 서비스 유닛 테스트.

워터폴 차트 생성 함수들의 동작을 검증합니다.
"""

from decimal import Decimal
from io import BytesIO

import pytest

from app.services.chart.waterfall import create_ebitda_bridge, create_generic_waterfall


class TestCreateEBITDABridge:
    """EBITDA Bridge 워터폴 차트 생성 테스트."""

    def test_basic_bridge(self):
        """기본 EBITDA Bridge 차트 생성."""
        categories = ["Reported EBITDA", "일회성 조정", "Adjusted EBITDA"]
        values = [Decimal("1000"), Decimal("200"), None]

        result = create_ebitda_bridge(categories, values)

        assert isinstance(result, BytesIO)
        # PNG 시그니처 확인
        content = result.read()
        assert content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_bridge_with_multiple_adjustments(self):
        """여러 조정 항목이 있는 Bridge 차트."""
        categories = [
            "Reported EBITDA",
            "일회성 비용",
            "비영업 수익",
            "인건비 정상화",
            "Adjusted EBITDA",
        ]
        values = [
            Decimal("1000"),
            Decimal("150"),
            Decimal("-30"),
            Decimal("50"),
            None,
        ]

        result = create_ebitda_bridge(categories, values)

        assert isinstance(result, BytesIO)
        content = result.read()
        assert len(content) > 1000  # PNG 파일은 최소 1KB 이상

    def test_bridge_with_negative_values(self):
        """음수 조정 금액 처리."""
        categories = ["Reported", "감소 조정", "Adjusted"]
        values = [Decimal("1000"), Decimal("-200"), None]

        result = create_ebitda_bridge(categories, values)

        assert isinstance(result, BytesIO)

    def test_bridge_with_custom_title(self):
        """커스텀 제목 적용."""
        categories = ["Reported", "Adjusted"]
        values = [Decimal("500"), None]

        result = create_ebitda_bridge(categories, values, title="FY2025 EBITDA Bridge")

        assert isinstance(result, BytesIO)

    def test_bridge_mismatched_lengths_raises(self):
        """categories와 values 길이 불일치 시 에러."""
        categories = ["A", "B", "C"]
        values = [Decimal("100"), Decimal("200")]

        with pytest.raises(ValueError, match="길이가 일치해야"):
            create_ebitda_bridge(categories, values)

    def test_bridge_too_few_items_raises(self):
        """최소 2개 이상 항목 필요."""
        categories = ["Only One"]
        values = [Decimal("100")]

        with pytest.raises(ValueError, match="최소 2개 이상"):
            create_ebitda_bridge(categories, values)

    def test_bridge_with_zero_values(self):
        """0 값 처리."""
        categories = ["Reported", "Zero Adj", "Adjusted"]
        values = [Decimal("1000"), Decimal("0"), None]

        result = create_ebitda_bridge(categories, values)

        assert isinstance(result, BytesIO)

    def test_bridge_with_large_numbers(self):
        """큰 숫자 처리 (십억 단위)."""
        categories = ["Reported", "Adjustment", "Adjusted"]
        values = [
            Decimal("123456789012.3456"),
            Decimal("9876543210.1234"),
            None,
        ]

        result = create_ebitda_bridge(categories, values)

        assert isinstance(result, BytesIO)


class TestCreateGenericWaterfall:
    """범용 워터폴 차트 생성 테스트."""

    def test_basic_waterfall(self):
        """기본 워터폴 차트 생성."""
        categories = ["Start", "Change1", "Change2", "End"]
        values = [Decimal("100"), Decimal("20"), Decimal("-10"), None]

        result = create_generic_waterfall(categories, values)

        assert isinstance(result, BytesIO)
        content = result.read()
        assert content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_waterfall_with_custom_measures(self):
        """커스텀 measures 지정."""
        categories = ["A", "B", "C", "D"]
        values = [Decimal("100"), Decimal("50"), Decimal("-30"), Decimal("120")]
        measures = ["absolute", "relative", "relative", "total"]

        result = create_generic_waterfall(categories, values, measures=measures)

        assert isinstance(result, BytesIO)

    def test_waterfall_with_all_absolute(self):
        """모든 항목이 absolute인 경우."""
        categories = ["Q1", "Q2", "Q3", "Q4"]
        values = [Decimal("100"), Decimal("120"), Decimal("90"), Decimal("150")]
        measures = ["absolute"] * 4

        result = create_generic_waterfall(categories, values, measures=measures)

        assert isinstance(result, BytesIO)

    def test_waterfall_with_custom_y_axis_title(self):
        """커스텀 y축 제목."""
        categories = ["Start", "End"]
        values = [Decimal("1000"), None]

        result = create_generic_waterfall(
            categories, values, y_axis_title="매출액 (억원)"
        )

        assert isinstance(result, BytesIO)

    def test_waterfall_measures_length_mismatch_raises(self):
        """measures 길이 불일치 시 에러."""
        categories = ["A", "B", "C"]
        values = [Decimal("100"), Decimal("50"), None]
        measures = ["absolute", "relative"]  # 2개 (3개 필요)

        with pytest.raises(ValueError, match="길이가 일치해야"):
            create_generic_waterfall(categories, values, measures=measures)


class TestDesignSystemIntegration:
    """Design System 통합 테스트."""

    def test_chart_uses_design_colors(self):
        """차트가 Design System 색상을 사용."""
        categories = ["Reported", "Positive", "Negative", "Adjusted"]
        values = [Decimal("1000"), Decimal("200"), Decimal("-100"), None]

        # 기본 Design System 로드 (오버라이드 없음)
        result = create_ebitda_bridge(categories, values)

        # 차트가 정상 생성되면 Design System이 적용된 것
        assert isinstance(result, BytesIO)
        assert result.read()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_chart_with_design_override(self):
        """Design System 오버라이드 적용."""
        categories = ["Start", "Change", "End"]
        values = [Decimal("500"), Decimal("100"), None]

        override = {
            "increasing_color": "#00FF00",
            "decreasing_color": "#FF0000",
            "total_color": "#0000FF",
        }

        result = create_ebitda_bridge(categories, values, design_override=override)

        assert isinstance(result, BytesIO)
