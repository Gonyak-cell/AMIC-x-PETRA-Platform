"""컴포넌트 테스트 — KPI/테이블/서브헤더/페이지 요소."""

import pytest

from src.design_renderer.components.financial_table import (
    render_financial_table_html,
)
from src.design_renderer.components.kpi_card import render_kpi_grid_html
from src.design_renderer.components.page_elements import (
    render_footer_html,
    render_horizontal_line_html,
    render_slide_title_html,
)
from src.design_renderer.components.sub_header_bar import render_sub_header_html
from src.design_renderer.design_tokens import DEFAULT_TOKENS
from src.design_renderer.im_document import NumberFormatConfig


@pytest.fixture
def tokens():
    return DEFAULT_TOKENS


@pytest.fixture
def number_config():
    return NumberFormatConfig()


class TestKpiCardHtml:
    """KPI 카드 HTML 렌더링."""

    def test_renders_html(self, tokens, number_config):
        """KPI 그리드 HTML 생성 (숫자 value)."""
        kpis = [
            {"label": "매출", "value": 150_000, "change": 0.25},
            {"label": "영업이익", "value": 28_000, "change": 0.40},
        ]
        result = render_kpi_grid_html(
            kpis, tokens=tokens, number_config=number_config
        )
        assert isinstance(result, str)
        assert "매출" in result

    def test_empty_kpis(self, tokens):
        """빈 KPI → 빈 결과 또는 최소 HTML."""
        result = render_kpi_grid_html([], tokens=tokens)
        assert isinstance(result, str)


class TestFinancialTableHtml:
    """재무 테이블 HTML 렌더링."""

    def test_renders_table(self, tokens, number_config):
        """헤더 + 데이터 행 포함 테이블 생성."""
        headers = ["항목", "2022", "2023", "2024"]
        rows = [
            {"label": "매출", "values": [100_000, 120_000, 150_000], "style": "normal"},
            {"label": "영업이익", "values": [15_000, 20_000, 28_000], "style": "normal"},
        ]
        result = render_financial_table_html(
            headers=headers, rows=rows, tokens=tokens, number_config=number_config
        )
        assert isinstance(result, str)
        assert "매출" in result
        assert "<table" in result or "<tr" in result

    def test_empty_rows(self, tokens, number_config):
        """빈 행 → 헤더만 포함 또는 빈 문자열."""
        result = render_financial_table_html(
            headers=["항목"], rows=[], tokens=tokens, number_config=number_config
        )
        assert isinstance(result, str)


class TestSubHeaderBar:
    """서브 헤더 바 HTML."""

    def test_renders_bar(self, tokens):
        """서브 헤더 바 HTML 생성."""
        result = render_sub_header_html("손익계산서", tokens=tokens)
        assert isinstance(result, str)
        assert "손익계산서" in result

    def test_empty_text(self, tokens):
        """빈 텍스트 → 빈 바."""
        result = render_sub_header_html("", tokens=tokens)
        assert isinstance(result, str)


class TestPageElements:
    """페이지 구성 요소."""

    def test_slide_title_html(self, tokens):
        """슬라이드 제목 HTML."""
        result = render_slide_title_html("재무 분석", tokens=tokens)
        assert "재무 분석" in result

    def test_footer_html(self, tokens):
        """푸터 HTML (페이지 번호 포함)."""
        result = render_footer_html(page_number=1, total_pages=10, tokens=tokens)
        assert isinstance(result, str)

    def test_horizontal_line_html(self):
        """수평선 HTML (인자 없음)."""
        result = render_horizontal_line_html()
        assert isinstance(result, str)
        assert "<hr" in result
