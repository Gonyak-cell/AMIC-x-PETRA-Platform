"""콘텐츠 오버플로우 감지 및 자동 분할.

AI 생성 콘텐츠가 슬라이드/페이지 영역을 초과할 때,
자동 분할·폰트 축소·테이블 행 분할 등의 전략을 적용한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens


# ---------------------------------------------------------------------------
# 데이터 구조
# ---------------------------------------------------------------------------


@dataclass
class ContentBlock:
    """렌더링 가능한 콘텐츠 블록."""

    content_type: str  # "text" | "table" | "chart" | "kpi_grid" | "image"
    data: Any = None
    estimated_height: float = 0.0  # inches (사전 계산 또는 estimate로 산출)
    font_size: int = 10  # 현재 폰트 크기 (pt)
    can_split: bool = True  # 분할 가능 여부 (차트/이미지는 False)


@dataclass
class SlideContent:
    """단일 슬라이드에 들어갈 콘텐츠 집합."""

    blocks: list[ContentBlock] = field(default_factory=list)
    title: str = ""
    is_continuation: bool = False  # True이면 제목에 " (cont'd)" 추가

    @property
    def display_title(self) -> str:
        if self.is_continuation and self.title:
            return f"{self.title} (cont'd)"
        return self.title

    @property
    def total_height(self) -> float:
        return sum(b.estimated_height for b in self.blocks)


# ---------------------------------------------------------------------------
# 높이 추정
# ---------------------------------------------------------------------------

# 추정 상수 (근사치, ~15% 오차 허용)
_LINE_HEIGHT_RATIO = 1.5  # 줄 간격 배수
_CHARS_PER_INCH = 11.0  # 10pt 기준 한 줄당 대략 문자 수 / inch
_TABLE_HEADER_HEIGHT = 0.35  # inches
_TABLE_ROW_HEIGHT = 0.26  # inches (IMPageLayout.table_row_height)
_CHART_DEFAULT_HEIGHT = 3.0  # inches
_KPI_ROW_HEIGHT = 1.2  # inches (4개 카드/행)
_IMAGE_DEFAULT_HEIGHT = 2.5  # inches
_BLOCK_GAP = 0.15  # inches (블록 간 간격)


def estimate_content_height(
    blocks: list[ContentBlock],
    *,
    tokens: IMDesignTokens | None = None,
) -> float:
    """콘텐츠 블록 리스트의 총 높이 추정 (inches).

    Args:
        blocks: ContentBlock 리스트.
        tokens: 디자인 토큰.

    Returns:
        추정 총 높이 (inches).
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    total = 0.0
    content_width = tokens.layout.content_width  # ~9.83"

    for i, block in enumerate(blocks):
        if block.estimated_height > 0:
            # 사전 계산된 높이 사용
            total += block.estimated_height
        else:
            # 타입별 추정
            height = _estimate_block_height(block, content_width)
            block.estimated_height = height
            total += height

        # 블록 간 간격
        if i < len(blocks) - 1:
            total += _BLOCK_GAP

    return total


def _estimate_block_height(block: ContentBlock, content_width: float) -> float:
    """개별 블록 높이 추정."""
    if block.content_type == "text":
        return _estimate_text_height(
            str(block.data or ""), block.font_size, content_width
        )
    if block.content_type == "table":
        return _estimate_table_height(block.data)
    if block.content_type == "chart":
        return _CHART_DEFAULT_HEIGHT
    if block.content_type == "kpi_grid":
        return _estimate_kpi_grid_height(block.data)
    if block.content_type == "image":
        return _IMAGE_DEFAULT_HEIGHT
    return 1.0  # 알 수 없는 타입 기본값


def _estimate_text_height(text: str, font_size: int, width_inches: float) -> float:
    """텍스트 높이 추정 (줄 수 기반, 단어 래핑 근사)."""
    if not text:
        return 0.0

    # pt → inches
    line_height_inches = (font_size / 72.0) * _LINE_HEIGHT_RATIO

    # 한 줄당 대략적 문자 수 (폰트 크기 고려)
    chars_per_line = int(width_inches * _CHARS_PER_INCH * (10.0 / font_size))
    if chars_per_line < 1:
        chars_per_line = 1

    # 줄 수 추정
    lines = 0
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines += 0.5  # 빈 줄은 절반
        else:
            lines += max(1, math.ceil(len(paragraph) / chars_per_line))

    return lines * line_height_inches


def _estimate_table_height(data: Any) -> float:
    """테이블 높이 추정."""
    if not data or not isinstance(data, list):
        return _TABLE_HEADER_HEIGHT + _TABLE_ROW_HEIGHT

    row_count = len(data)
    has_header = row_count > 1
    header = _TABLE_HEADER_HEIGHT if has_header else 0
    return header + row_count * _TABLE_ROW_HEIGHT


def _estimate_kpi_grid_height(data: Any) -> float:
    """KPI 그리드 높이 추정 (행당 4개 카드)."""
    if not data or not isinstance(data, list):
        return _KPI_ROW_HEIGHT

    card_count = len(data)
    rows = math.ceil(card_count / 4)
    return rows * _KPI_ROW_HEIGHT


# ---------------------------------------------------------------------------
# 콘텐츠 분할
# ---------------------------------------------------------------------------


def split_content_to_slides(
    blocks: list[ContentBlock],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    max_height: float | None = None,
) -> list[SlideContent]:
    """콘텐츠를 여러 슬라이드로 자동 분할.

    Args:
        blocks: ContentBlock 리스트.
        title: 슬라이드 제목.
        tokens: 디자인 토큰.
        max_height: 최대 높이 (inches). None이면 layout에서 자동.

    Returns:
        SlideContent 리스트. 각 슬라이드의 총 높이가 max_height 이하.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    if max_height is None:
        max_height = tokens.layout.content_height  # ~5.43"

    # 높이 추정 보장
    estimate_content_height(blocks, tokens=tokens)

    slides: list[SlideContent] = []
    current_blocks: list[ContentBlock] = []
    current_height = 0.0
    is_first = True

    for block in blocks:
        block_height = block.estimated_height + (_BLOCK_GAP if current_blocks else 0)

        if current_height + block_height <= max_height or not current_blocks:
            # 현재 슬라이드에 추가
            current_blocks.append(block)
            current_height += block_height
        else:
            # 현재 슬라이드 마감, 새 슬라이드 시작
            slides.append(
                SlideContent(
                    blocks=current_blocks,
                    title=title,
                    is_continuation=not is_first,
                )
            )
            is_first = False

            # 분할 가능한 블록이면 분할 시도
            if block.content_type == "table" and block.can_split:
                sub_slides = _split_table_block(block, title, max_height, tokens)
                slides.extend(sub_slides)
                current_blocks = []
                current_height = 0.0
            else:
                current_blocks = [block]
                current_height = block.estimated_height

    # 남은 블록
    if current_blocks:
        slides.append(
            SlideContent(
                blocks=current_blocks,
                title=title,
                is_continuation=not is_first,
            )
        )

    # 슬라이드가 비어 있으면 빈 슬라이드 하나
    if not slides:
        slides.append(SlideContent(title=title))

    return slides


def _split_table_block(
    block: ContentBlock,
    title: str,
    max_height: float,
    tokens: IMDesignTokens,
) -> list[SlideContent]:
    """테이블 블록을 여러 슬라이드로 분할 (헤더 반복)."""
    data = block.data
    if not data or not isinstance(data, list) or len(data) < 2:
        return [SlideContent(blocks=[block], title=title, is_continuation=True)]

    header = data[0]
    body_rows = data[1:]

    # 슬라이드당 최대 행 수 계산
    available = max_height - _TABLE_HEADER_HEIGHT
    max_rows = max(1, int(available / _TABLE_ROW_HEIGHT))

    slides: list[SlideContent] = []
    for i in range(0, len(body_rows), max_rows):
        chunk = body_rows[i : i + max_rows]
        table_data = [header] + chunk
        new_block = ContentBlock(
            content_type="table",
            data=table_data,
            estimated_height=_estimate_table_height(table_data),
            font_size=block.font_size,
            can_split=False,  # 이미 분할됨
        )
        slides.append(
            SlideContent(
                blocks=[new_block],
                title=title,
                is_continuation=True,
            )
        )

    return slides


# ---------------------------------------------------------------------------
# 폰트 크기 자동 조정
# ---------------------------------------------------------------------------


def auto_adjust_font_size(
    blocks: list[ContentBlock],
    *,
    tokens: IMDesignTokens | None = None,
    target_height: float | None = None,
) -> list[ContentBlock]:
    """콘텐츠가 한 슬라이드에 맞도록 폰트 크기 자동 조정.

    10pt → 9pt → 8pt 순서로 축소, 7pt 하한.
    차트/이미지는 리사이즈하지 않는다.

    Args:
        blocks: ContentBlock 리스트.
        tokens: 디자인 토큰.
        target_height: 목표 높이. None이면 layout에서 자동.

    Returns:
        폰트 크기가 조정된 새 ContentBlock 리스트.
        7pt에서도 초과하면 원본 반환 (호출자가 split 사용).
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    if target_height is None:
        target_height = tokens.layout.content_height

    min_font = tokens.font_sizes.minimum  # 7pt

    # 현재 높이 확인
    current = estimate_content_height(blocks, tokens=tokens)
    if current <= target_height:
        return blocks

    # 축소 시도: 10 → 9 → 8 → 7
    for size in (9, 8, min_font):
        adjusted = _adjust_blocks_font(blocks, size)
        # 높이 재계산
        for b in adjusted:
            b.estimated_height = 0.0  # 리셋
        h = estimate_content_height(adjusted, tokens=tokens)
        if h <= target_height:
            return adjusted

    # 7pt에서도 초과 → 원본 반환
    return blocks


def _adjust_blocks_font(
    blocks: list[ContentBlock], font_size: int
) -> list[ContentBlock]:
    """텍스트/테이블 블록의 폰트 크기를 조정한 복사본 반환."""
    result: list[ContentBlock] = []
    for block in blocks:
        if block.content_type in ("text", "table"):
            new_block = ContentBlock(
                content_type=block.content_type,
                data=block.data,
                estimated_height=0.0,  # 재계산 필요
                font_size=font_size,
                can_split=block.can_split,
            )
            result.append(new_block)
        else:
            # 차트/이미지는 그대로
            result.append(block)
    return result
