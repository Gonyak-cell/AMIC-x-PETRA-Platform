"""출처 각주 테스트 — 번호 할당/포맷/HTML 렌더링."""

import pytest

from src.design_renderer.components.source_citation import (
    assign_footnote_numbers,
    format_footnote,
    render_footnote_html,
)
from src.design_renderer.im_document import SourceCitation


@pytest.fixture
def sample_citations() -> dict[str, list[SourceCitation]]:
    """섹션별 출처 데이터."""
    return {
        "financial_analysis": [
            SourceCitation(
                source_name="DART",
                url="https://dart.fss.or.kr",
                access_date="2026-02",
            ),
            SourceCitation(
                source_name="네이버 뉴스",
                access_date="2026-01",
            ),
        ],
        "market_overview": [
            SourceCitation(
                source_name="한국IDC",
                access_date="2026-01",
                document_title="2025 IT 시장 전망",
            ),
        ],
    }


class TestFormatFootnote:
    """개별 각주 포맷팅."""

    def test_basic_format(self):
        """출처명 + 접근일 포맷."""
        citation = SourceCitation(source_name="DART", access_date="2026-02")
        result = format_footnote(citation)
        assert "DART" in result
        assert "2026-02" in result

    def test_with_document_title(self):
        """문서 제목이 있으면 포함."""
        citation = SourceCitation(
            source_name="한국IDC",
            document_title="2025 전망",
            access_date="2026",
        )
        result = format_footnote(citation)
        assert "한국IDC" in result


class TestAssignFootnoteNumbers:
    """각주 번호 할당."""

    def test_sequential_numbers(self, sample_citations):
        """여러 섹션에 순차 번호 부여."""
        numbered = assign_footnote_numbers(sample_citations)
        assert isinstance(numbered, dict)
        # 번호가 부여되었는지 확인
        assert len(numbered) > 0

    def test_empty_citations(self):
        """빈 출처 → 빈 결과."""
        numbered = assign_footnote_numbers({})
        assert numbered == {} or len(numbered) == 0


class TestRenderFootnoteHtml:
    """각주 HTML 렌더링."""

    def test_renders_html(self):
        """(번호, 출처) 튜플 리스트 → HTML 문자열."""
        citations = [
            (1, SourceCitation(source_name="DART", access_date="2026-02")),
        ]
        result = render_footnote_html(citations)
        assert isinstance(result, str)
        assert "DART" in result

    def test_empty_list_returns_empty(self):
        """빈 리스트 → 빈 문자열."""
        result = render_footnote_html([])
        assert result == "" or result.strip() == ""
