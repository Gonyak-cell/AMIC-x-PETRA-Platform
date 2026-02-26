"""Shape 매퍼 — 마스터 PPTX 템플릿의 shape를 자동 분석한다.

각 슬라이드의 교체 가능한 shape(텍스트, 차트, 테이블)를 탐색하여
데이터 삽입 포인트를 자동 매핑한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShapeSlot:
    """교체 가능한 shape의 메타데이터."""

    slide_idx: int
    shape_name: str
    shape_type: str  # "chart", "table", "text", "auto_shape", "placeholder", "group"
    chart_type: str | None = None  # "COLUMN_CLUSTERED", "DOUGHNUT", etc.
    text_preview: str | None = None  # 첫 80자 미리보기
    table_size: tuple[int, int] | None = None  # (rows, cols)
    data_key: str | None = None  # 매핑 파일에서 설정


def analyze_template(pptx_path: Path) -> list[ShapeSlot]:
    """마스터 PPTX 템플릿의 모든 교체 가능한 shape를 분석한다.

    Args:
        pptx_path: PPTX 파일 경로.

    Returns:
        ShapeSlot 목록 (슬라이드 순서대로).
    """
    prs = Presentation(str(pptx_path))
    slots: list[ShapeSlot] = []

    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            slot = _classify_shape(slide_idx, shape)
            if slot is not None:
                slots.append(slot)

    logger.info(
        "템플릿 분석 완료: %s — %d슬라이드, %d개 교체 가능 shape",
        pptx_path.name,
        len(prs.slides),
        len(slots),
    )
    return slots


def create_shape_map(pptx_path: Path) -> dict[str, list[ShapeSlot]]:
    """slide_idx별 shape_name → ShapeSlot 매핑을 생성한다.

    Returns:
        {slide_idx: [ShapeSlot, ...]} 형태의 딕셔너리.
    """
    slots = analyze_template(pptx_path)
    result: dict[str, list[ShapeSlot]] = {}
    for slot in slots:
        key = str(slot.slide_idx)
        if key not in result:
            result[key] = []
        result[key].append(slot)
    return result


def get_charts(pptx_path: Path) -> list[ShapeSlot]:
    """차트 shape만 필터링하여 반환한다."""
    return [s for s in analyze_template(pptx_path) if s.shape_type == "chart"]


def get_tables(pptx_path: Path) -> list[ShapeSlot]:
    """테이블 shape만 필터링하여 반환한다."""
    return [s for s in analyze_template(pptx_path) if s.shape_type == "table"]


def get_text_shapes(pptx_path: Path) -> list[ShapeSlot]:
    """텍스트 shape만 필터링하여 반환한다."""
    return [
        s for s in analyze_template(pptx_path)
        if s.shape_type in ("text", "auto_shape", "placeholder")
    ]


# ── 내부 함수 ───────────────────────────────────────────────────────────────


def _classify_shape(slide_idx: int, shape: object) -> ShapeSlot | None:
    """shape를 분류하여 ShapeSlot을 반환한다. 교체 불가능하면 None."""
    # 차트
    if hasattr(shape, "has_chart") and shape.has_chart:
        chart_type_name = "UNKNOWN"
        try:
            chart_type_name = str(shape.chart.chart_type).split("(")[0].strip()
        except Exception:
            pass
        return ShapeSlot(
            slide_idx=slide_idx,
            shape_name=shape.name,
            shape_type="chart",
            chart_type=chart_type_name,
        )

    # 테이블
    if hasattr(shape, "has_table") and shape.has_table:
        table = shape.table
        num_rows = len(list(table.rows))
        num_cols = len(table.columns)
        return ShapeSlot(
            slide_idx=slide_idx,
            shape_name=shape.name,
            shape_type="table",
            table_size=(num_rows, num_cols),
        )

    # 텍스트 프레임
    if hasattr(shape, "has_text_frame") and shape.has_text_frame:
        text = shape.text_frame.text.strip()
        if not text:
            return None  # 빈 텍스트 shape는 스킵

        # shape 유형 분류
        shape_type_val = getattr(shape, "shape_type", None)
        if shape_type_val == MSO_SHAPE_TYPE.PLACEHOLDER:
            slot_type = "placeholder"
        elif shape_type_val == MSO_SHAPE_TYPE.AUTO_SHAPE:
            slot_type = "auto_shape"
        elif shape_type_val == MSO_SHAPE_TYPE.TEXT_BOX:
            slot_type = "text"
        else:
            slot_type = "text"

        return ShapeSlot(
            slide_idx=slide_idx,
            shape_name=shape.name,
            shape_type=slot_type,
            text_preview=text[:80],
        )

    return None
