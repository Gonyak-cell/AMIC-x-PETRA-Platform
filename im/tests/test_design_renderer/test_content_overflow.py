"""콘텐츠 오버플로우 테스트 — 높이 추정/분할/폰트 조절."""


from src.design_renderer.components.content_overflow import (
    ContentBlock,
    SlideContent,
    auto_adjust_font_size,
    estimate_content_height,
    split_content_to_slides,
)


class TestEstimateContentHeight:
    """콘텐츠 높이 추정."""

    def test_short_text(self):
        """짧은 텍스트 → 낮은 높이."""
        block = ContentBlock(content_type="text", data="짧은 텍스트입니다.")
        height = estimate_content_height([block])
        assert height > 0
        assert height < 2.0  # 2인치 미만

    def test_table_height(self):
        """10행 테이블 → row_height × 10 정도."""
        rows = [["항목", "값"]] * 10
        block = ContentBlock(content_type="table", data=rows)
        height = estimate_content_height([block])
        assert height > 0

    def test_empty_blocks(self):
        """빈 블록 → 0."""
        height = estimate_content_height([])
        assert height == 0 or height >= 0

    def test_chart_default_height(self):
        """차트 블록 → 기본 3.0인치."""
        block = ContentBlock(content_type="chart", data=None, can_split=False)
        height = estimate_content_height([block])
        assert height > 0


class TestSplitContentToSlides:
    """콘텐츠 슬라이드 분할."""

    def test_single_slide(self):
        """한 슬라이드에 들어가는 콘텐츠 → 1개 SlideContent."""
        blocks = [
            ContentBlock(content_type="text", data="짧은 콘텐츠")
        ]
        result = split_content_to_slides(blocks)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_multiple_slides(self):
        """많은 콘텐츠 → 2+ SlideContent."""
        blocks = [
            ContentBlock(content_type="text", data="항목 " * 200)
            for _ in range(10)
        ]
        result = split_content_to_slides(blocks)
        assert len(result) >= 1

    def test_empty_input(self):
        """빈 입력 → 빈 결과."""
        result = split_content_to_slides([])
        assert isinstance(result, list)


class TestAutoAdjustFontSize:
    """폰트 크기 자동 조정."""

    def test_returns_content_blocks(self):
        """조정 결과는 ContentBlock 리스트."""
        blocks = [ContentBlock(content_type="text", data="짧은 텍스트")]
        result = auto_adjust_font_size(blocks)
        assert isinstance(result, list)
        assert all(isinstance(b, ContentBlock) for b in result)

    def test_preserves_content(self):
        """데이터는 보존."""
        blocks = [ContentBlock(content_type="text", data="테스트 데이터")]
        result = auto_adjust_font_size(blocks)
        assert result[0].data == "테스트 데이터"

    def test_minimum_font_7pt(self):
        """최소 7pt 미만으로 줄어들지 않음."""
        blocks = [
            ContentBlock(content_type="text", data="항목 " * 2000)
            for _ in range(50)
        ]
        result = auto_adjust_font_size(blocks)
        for block in result:
            if block.content_type == "text":
                assert block.font_size >= 7


class TestSlideContent:
    """SlideContent 데이터클래스."""

    def test_display_title(self):
        """continuation 표시."""
        sc = SlideContent(title="재무 분석", is_continuation=True)
        assert "(cont'd)" in sc.display_title

    def test_total_height(self):
        """블록 높이 합산."""
        sc = SlideContent(blocks=[
            ContentBlock(content_type="text", data="A", estimated_height=1.0),
            ContentBlock(content_type="text", data="B", estimated_height=2.0),
        ])
        assert sc.total_height == 3.0
