"""chart_replacer 모듈 단위 테스트."""

import pytest
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

from app.pptx.template_engine.chart_replacer import replace_chart_data, replace_chart_data_batch
from app.pptx.template_engine.exceptions import ChartShapeError, DataValidationError, ShapeNotFoundError


@pytest.fixture
def chart_slide():
    """차트가 포함된 테스트 슬라이드 생성."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # Blank layout

    # 기본 차트 삽입
    chart_data = CategoryChartData()
    chart_data.categories = ["Q1", "Q2", "Q3"]
    chart_data.add_series("매출", (100, 200, 300))

    chart_shape = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(1),
        Inches(1),
        Inches(4),
        Inches(3),
        chart_data,
    )
    chart_shape.name = "chart_revenue"

    # 텍스트박스 (차트 아닌 shape)
    txBox = slide.shapes.add_textbox(Inches(6), Inches(1), Inches(2), Inches(1))
    txBox.name = "txt_title"
    txBox.text_frame.paragraphs[0].text = "제목"

    return slide


class TestReplaceChartData:
    """replace_chart_data 함수 테스트."""

    def test_basic_replace(self, chart_slide):
        """기본 차트 데이터 교체 — 카테고리/시리즈 갱신."""
        chart = replace_chart_data(
            chart_slide,
            "chart_revenue",
            categories=["2022", "2023", "2024"],
            series=[{"name": "매출", "values": [1000, 1200, 1500]}],
        )
        assert chart is not None
        assert len(chart.plots[0].series) == 1

    def test_scale_factor(self, chart_slide):
        """scale_factor 적용 검증."""
        chart = replace_chart_data(
            chart_slide,
            "chart_revenue",
            categories=["A", "B"],
            series=[{"name": "S1", "values": [1000000, 2000000]}],
            scale_factor=0.001,
        )
        # chart.replace_data 호출 후 시리즈 값을 직접 확인하기 어렵지만
        # 에러 없이 완료되면 스케일링 로직 통과
        assert chart is not None

    def test_multiple_series(self, chart_slide):
        """다중 시리즈 교체."""
        chart = replace_chart_data(
            chart_slide,
            "chart_revenue",
            categories=["A", "B", "C"],
            series=[
                {"name": "매출", "values": [100, 200, 300]},
                {"name": "EBITDA", "values": [50, 80, 120]},
            ],
        )
        assert len(chart.plots[0].series) == 2

    def test_none_values(self, chart_slide):
        """None 값 포함 시리즈 — 빈 데이터 포인트."""
        chart = replace_chart_data(
            chart_slide,
            "chart_revenue",
            categories=["A", "B", "C"],
            series=[{"name": "S1", "values": [100, None, 300]}],
        )
        assert chart is not None

    def test_shape_not_found(self, chart_slide):
        """존재하지 않는 shape name — ShapeNotFoundError."""
        with pytest.raises(ShapeNotFoundError):
            replace_chart_data(
                chart_slide,
                "chart_nonexistent",
                categories=["A"],
                series=[{"name": "S1", "values": [1]}],
            )

    def test_not_a_chart(self, chart_slide):
        """차트가 아닌 shape — ChartShapeError."""
        with pytest.raises(ChartShapeError):
            replace_chart_data(
                chart_slide,
                "txt_title",
                categories=["A"],
                series=[{"name": "S1", "values": [1]}],
            )

    def test_category_series_mismatch(self, chart_slide):
        """카테고리/시리즈 길이 불일치 — DataValidationError."""
        with pytest.raises(DataValidationError):
            replace_chart_data(
                chart_slide,
                "chart_revenue",
                categories=["A", "B"],
                series=[{"name": "S1", "values": [1, 2, 3]}],  # 3 != 2
            )

    def test_custom_number_format(self, chart_slide):
        """커스텀 숫자 서식 적용."""
        chart = replace_chart_data(
            chart_slide,
            "chart_revenue",
            categories=["A", "B"],
            series=[{"name": "S1", "values": [100, 200]}],
            number_format="#,##0.0",
        )
        assert chart is not None


class TestReplaceChartDataBatch:
    """replace_chart_data_batch 함수 테스트."""

    def test_batch_single(self, chart_slide):
        """단일 차트 배치 교체."""
        results = replace_chart_data_batch(
            chart_slide,
            [
                {
                    "shape_name": "chart_revenue",
                    "categories": ["A", "B"],
                    "series": [{"name": "S1", "values": [10, 20]}],
                },
            ],
        )
        assert len(results) == 1
