"""Chart Renderer 테스트 — FDD-1301, FDD-1302, FDD-1303.

테스트 ID 규칙: T-CHART-{번호}
"""

from decimal import Decimal
from io import BytesIO

import pytest

from app.renderers.report_builder import ChartBlock, ChartData, ChartType
from app.services.chart import (
    CHART_RENDERER_VERSION,
    ChartSpec,
    create_bar_chart,
    create_donut_chart,
    create_grouped_bar_chart,
    create_pie_chart,
    create_single_line_chart,
    create_stacked_bar_chart,
    create_trend_chart,
    render_chart,
    render_chart_block,
    render_chart_to_base64,
    validate_chart_data,
)
from app.services.chart.waterfall import create_ebitda_bridge, create_generic_waterfall


class TestChartRendererVersion:
    """T-CHART-01: 버전 정보 테스트."""

    def test_version_exists(self):
        """버전 문자열 존재."""
        assert CHART_RENDERER_VERSION is not None
        assert isinstance(CHART_RENDERER_VERSION, str)

    def test_version_format(self):
        """버전 포맷 (SemVer)."""
        parts = CHART_RENDERER_VERSION.split(".")
        assert len(parts) == 3


class TestChartSpec:
    """T-CHART-02: ChartSpec 클래스 테스트."""

    def test_spec_with_string_type(self):
        """문자열 차트 타입."""
        spec = ChartSpec(
            chart_type="waterfall",
            title="Test",
            categories=["A", "B"],
            values=[Decimal("100"), None],
        )
        assert spec.chart_type == ChartType.WATERFALL

    def test_spec_with_enum_type(self):
        """Enum 차트 타입."""
        spec = ChartSpec(
            chart_type=ChartType.BAR,
            title="Bar Chart",
            categories=["Q1", "Q2"],
            values=[Decimal("50"), Decimal("60")],
        )
        assert spec.chart_type == ChartType.BAR

    def test_spec_with_series(self):
        """다중 시리즈 스펙."""
        spec = ChartSpec(
            chart_type=ChartType.LINE,
            title="Multi-series",
            categories=["Jan", "Feb"],
            series=[
                {"name": "Revenue", "values": [100, 110]},
                {"name": "Cost", "values": [80, 85]},
            ],
        )
        assert len(spec.series) == 2


class TestWaterfallChart:
    """T-CHART-03: 워터폴 차트 테스트."""

    def test_ebitda_bridge_basic(self):
        """기본 EBITDA Bridge."""
        buffer = create_ebitda_bridge(
            categories=["Reported", "Adj 1", "Adj 2", "Adjusted"],
            values=[Decimal("1000"), Decimal("100"), Decimal("-50"), None],
            title="EBITDA Bridge",
        )
        assert isinstance(buffer, BytesIO)
        assert buffer.getbuffer().nbytes > 0

    def test_generic_waterfall(self):
        """범용 워터폴 차트."""
        buffer = create_generic_waterfall(
            categories=["Start", "Change 1", "Change 2", "End"],
            values=[Decimal("500"), Decimal("100"), Decimal("-50"), None],
            title="Waterfall",
        )
        assert isinstance(buffer, BytesIO)

    def test_waterfall_validation_error(self):
        """워터폴 검증 오류."""
        with pytest.raises(ValueError, match="길이가 일치"):
            create_ebitda_bridge(
                categories=["A", "B"],
                values=[Decimal("100")],  # 길이 불일치
            )


class TestLineChart:
    """T-CHART-04: 라인 차트 테스트."""

    def test_single_line(self):
        """단일 라인 차트."""
        buffer = create_single_line_chart(
            categories=["Jan", "Feb", "Mar", "Apr"],
            values=[Decimal("100"), Decimal("110"), Decimal("105"), Decimal("120")],
            title="Revenue Trend",
        )
        assert isinstance(buffer, BytesIO)
        assert buffer.getbuffer().nbytes > 0

    def test_multi_series_line(self):
        """다중 시리즈 라인 차트."""
        buffer = create_trend_chart(
            categories=["Q1", "Q2", "Q3", "Q4"],
            series=[
                {"name": "Revenue", "values": [100, 110, 120, 130]},
                {"name": "EBITDA", "values": [20, 22, 25, 28]},
            ],
            title="Performance Trend",
        )
        assert isinstance(buffer, BytesIO)

    def test_line_with_none_values(self):
        """None 값 포함 라인 차트."""
        buffer = create_single_line_chart(
            categories=["A", "B", "C", "D"],
            values=[Decimal("100"), None, Decimal("120"), Decimal("130")],
            title="Sparse Data",
        )
        assert isinstance(buffer, BytesIO)


class TestBarChart:
    """T-CHART-05: 바 차트 테스트."""

    def test_basic_bar(self):
        """기본 바 차트."""
        buffer = create_bar_chart(
            categories=["Product A", "Product B", "Product C"],
            values=[Decimal("100"), Decimal("150"), Decimal("80")],
            title="Sales by Product",
        )
        assert isinstance(buffer, BytesIO)
        assert buffer.getbuffer().nbytes > 0

    def test_horizontal_bar(self):
        """수평 바 차트."""
        buffer = create_bar_chart(
            categories=["A", "B", "C"],
            values=[Decimal("30"), Decimal("50"), Decimal("40")],
            title="Horizontal Bar",
            horizontal=True,
        )
        assert isinstance(buffer, BytesIO)

    def test_grouped_bar(self):
        """그룹 바 차트."""
        buffer = create_grouped_bar_chart(
            categories=["Q1", "Q2", "Q3"],
            series=[
                {"name": "2024", "values": [100, 110, 120]},
                {"name": "2025", "values": [105, 115, 130]},
            ],
            title="Quarterly Comparison",
        )
        assert isinstance(buffer, BytesIO)

    def test_stacked_bar(self):
        """누적 바 차트."""
        buffer = create_stacked_bar_chart(
            categories=["Jan", "Feb", "Mar"],
            series=[
                {"name": "Product A", "values": [50, 60, 55]},
                {"name": "Product B", "values": [30, 35, 40]},
            ],
            title="Stacked Revenue",
        )
        assert isinstance(buffer, BytesIO)


class TestPieChart:
    """T-CHART-06: 파이/도넛 차트 테스트."""

    def test_basic_pie(self):
        """기본 파이 차트."""
        buffer = create_pie_chart(
            labels=["Revenue", "COGS", "SG&A", "Other"],
            values=[Decimal("60"), Decimal("25"), Decimal("10"), Decimal("5")],
            title="Cost Breakdown",
        )
        assert isinstance(buffer, BytesIO)
        assert buffer.getbuffer().nbytes > 0

    def test_donut_chart(self):
        """도넛 차트."""
        buffer = create_donut_chart(
            labels=["Debt", "Cash"],
            values=[Decimal("100"), Decimal("30")],
            title="Net Debt Composition",
            center_text="Net Debt\n70M",
        )
        assert isinstance(buffer, BytesIO)

    def test_pie_with_custom_colors(self):
        """커스텀 색상 파이 차트."""
        buffer = create_pie_chart(
            labels=["A", "B", "C"],
            values=[Decimal("40"), Decimal("35"), Decimal("25")],
            title="Custom Colors",
            colors_list=["#FF0000", "#00FF00", "#0000FF"],
        )
        assert isinstance(buffer, BytesIO)


class TestRenderChartFacade:
    """T-CHART-07: render_chart 파사드 테스트."""

    def test_render_waterfall(self):
        """파사드로 워터폴 렌더링."""
        spec = ChartSpec(
            chart_type=ChartType.WATERFALL,
            title="Waterfall",
            categories=["Start", "Adj", "End"],
            values=[Decimal("100"), Decimal("10"), None],
        )
        buffer = render_chart(spec)
        assert isinstance(buffer, BytesIO)

    def test_render_bar(self):
        """파사드로 바 렌더링."""
        spec = ChartSpec(
            chart_type=ChartType.BAR,
            title="Bar",
            categories=["A", "B"],
            values=[Decimal("50"), Decimal("75")],
        )
        buffer = render_chart(spec)
        assert isinstance(buffer, BytesIO)

    def test_render_line(self):
        """파사드로 라인 렌더링."""
        spec = ChartSpec(
            chart_type=ChartType.LINE,
            title="Line",
            categories=["1", "2", "3"],
            values=[Decimal("10"), Decimal("20"), Decimal("15")],
        )
        buffer = render_chart(spec)
        assert isinstance(buffer, BytesIO)

    def test_render_pie(self):
        """파사드로 파이 렌더링."""
        spec = ChartSpec(
            chart_type=ChartType.PIE,
            title="Pie",
            categories=["X", "Y", "Z"],
            values=[Decimal("33"), Decimal("33"), Decimal("34")],
        )
        buffer = render_chart(spec)
        assert isinstance(buffer, BytesIO)

    def test_render_donut(self):
        """파사드로 도넛 렌더링."""
        spec = ChartSpec(
            chart_type=ChartType.PIE,
            title="Donut",
            categories=["A", "B"],
            values=[Decimal("60"), Decimal("40")],
            config={"donut": True, "hole_size": 0.5},
        )
        buffer = render_chart(spec)
        assert isinstance(buffer, BytesIO)


class TestRenderChartToBase64:
    """T-CHART-08: base64 렌더링 테스트."""

    def test_base64_output(self):
        """base64 출력."""
        spec = ChartSpec(
            chart_type=ChartType.BAR,
            title="Test",
            categories=["A"],
            values=[Decimal("100")],
        )
        result = render_chart_to_base64(spec)
        assert isinstance(result, str)
        assert len(result) > 100  # base64 문자열


class TestRenderChartBlock:
    """T-CHART-09: ChartBlock 렌더링 테스트."""

    def test_block_without_image(self):
        """이미지 없는 블록 렌더링."""
        block = ChartBlock(
            chart_type=ChartType.WATERFALL,
            title="EBITDA Bridge",
            data=ChartData(
                categories=["Start", "Adj", "End"],
                values=[Decimal("100"), Decimal("10"), None],
            ),
        )
        result = render_chart_block(block)
        assert result.image_base64 is not None
        assert len(result.image_base64) > 100

    def test_block_with_existing_image(self):
        """기존 이미지 유지."""
        existing_image = "existing_base64_image"
        block = ChartBlock(
            chart_type=ChartType.BAR,
            title="Test",
            image_base64=existing_image,
        )
        result = render_chart_block(block)
        assert result.image_base64 == existing_image


class TestValidateChartData:
    """T-CHART-10: 차트 데이터 검증 테스트."""

    def test_valid_data(self):
        """유효한 데이터."""
        spec = ChartSpec(
            chart_type=ChartType.BAR,
            categories=["A", "B", "C"],
            values=[Decimal("100"), Decimal("200"), Decimal("150")],
        )
        errors = validate_chart_data(spec)
        assert len(errors) == 0

    def test_empty_categories(self):
        """빈 카테고리."""
        spec = ChartSpec(
            chart_type=ChartType.BAR,
            categories=[],
            values=[Decimal("100")],
        )
        errors = validate_chart_data(spec)
        assert any("empty" in e.lower() for e in errors)

    def test_mismatched_counts(self):
        """카테고리/값 수 불일치."""
        spec = ChartSpec(
            chart_type=ChartType.BAR,
            categories=["A", "B", "C"],
            values=[Decimal("100"), Decimal("200")],
        )
        errors = validate_chart_data(spec)
        assert any("count" in e.lower() for e in errors)

    def test_series_mismatched_counts(self):
        """시리즈 값 수 불일치."""
        spec = ChartSpec(
            chart_type=ChartType.LINE,
            categories=["A", "B", "C"],
            series=[{"name": "S1", "values": [1, 2]}],  # 2개 값, 3개 카테고리
        )
        errors = validate_chart_data(spec)
        assert any("series" in e.lower() for e in errors)


class TestChartEdgeCases:
    """T-CHART-11: 엣지 케이스 테스트."""

    def test_negative_values(self):
        """음수 값 처리."""
        buffer = create_bar_chart(
            categories=["Profit", "Loss"],
            values=[Decimal("100"), Decimal("-50")],
            title="P&L",
        )
        assert isinstance(buffer, BytesIO)

    def test_zero_values(self):
        """0 값 처리."""
        buffer = create_pie_chart(
            labels=["A", "B", "C"],
            values=[Decimal("50"), Decimal("0"), Decimal("50")],
            title="With Zero",
        )
        assert isinstance(buffer, BytesIO)

    def test_large_values(self):
        """큰 값 처리."""
        buffer = create_bar_chart(
            categories=["Revenue"],
            values=[Decimal("1000000000000")],  # 1조
            title="Large Value",
        )
        assert isinstance(buffer, BytesIO)

    def test_many_categories(self):
        """많은 카테고리."""
        categories = [f"Item {i}" for i in range(50)]
        values = [Decimal(str(i * 10)) for i in range(50)]
        buffer = create_bar_chart(
            categories=categories,
            values=values,
            title="Many Items",
        )
        assert isinstance(buffer, BytesIO)


class TestChartKorean:
    """T-CHART-12: 한글 차트 테스트."""

    def test_korean_title(self):
        """한글 제목."""
        buffer = create_bar_chart(
            categories=["매출", "비용", "영업이익"],
            values=[Decimal("100"), Decimal("-70"), Decimal("30")],
            title="손익 현황",
        )
        assert isinstance(buffer, BytesIO)

    def test_korean_labels(self):
        """한글 레이블."""
        buffer = create_pie_chart(
            labels=["제품A", "제품B", "제품C"],
            values=[Decimal("40"), Decimal("35"), Decimal("25")],
            title="제품별 매출 비중",
        )
        assert isinstance(buffer, BytesIO)


class TestDesignSystemIntegration:
    """T-CHART-13: Design System 통합 테스트."""

    def test_colors_applied(self):
        """디자인 시스템 색상 적용 (간접 확인)."""
        # 차트 생성이 성공하면 색상이 적용된 것
        buffer = create_ebitda_bridge(
            categories=["Start", "Adj", "End"],
            values=[Decimal("100"), Decimal("10"), None],
        )
        assert buffer.getbuffer().nbytes > 0

    def test_design_override(self):
        """디자인 오버라이드."""
        buffer = create_ebitda_bridge(
            categories=["A", "B", "C"],
            values=[Decimal("100"), Decimal("20"), None],
            design_override={"title_size": 20, "background": "#F0F0F0"},
        )
        assert isinstance(buffer, BytesIO)
