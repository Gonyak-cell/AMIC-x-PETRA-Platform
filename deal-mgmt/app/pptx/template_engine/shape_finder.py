"""Shape Name 기반 탐색 유틸리티.

템플릿 PPTX 내 도형을 name으로 찾거나, 개발 시 shape 구조를 카탈로그화한다.
"""

from __future__ import annotations

import logging
from typing import Any

from .exceptions import ShapeNotFoundError

logger = logging.getLogger(__name__)


def find_shape_by_name(slide: Any, name: str) -> Any:
    """슬라이드에서 name이 일치하는 shape를 반환.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        name: shape.name 값 (예: "chart_revenue", "img_logo").

    Returns:
        일치하는 shape 객체.

    Raises:
        ShapeNotFoundError: 일치하는 shape가 없을 때.
    """
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    existing = [s.name for s in slide.shapes]
    raise ShapeNotFoundError(f"슬라이드에서 '{name}' shape를 찾을 수 없습니다. 존재하는 shape: {existing}")


def find_shapes_by_prefix(slide: Any, prefix: str) -> list[Any]:
    """슬라이드에서 name이 prefix로 시작하는 모든 shape 반환.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        prefix: shape.name 접두사 (예: "img_" → 모든 이미지 플레이스홀더).

    Returns:
        일치하는 shape 리스트 (이름순 정렬, 빈 리스트 가능).
    """
    shapes = [s for s in slide.shapes if s.name.startswith(prefix)]
    shapes.sort(key=lambda s: s.name)
    return shapes


def get_shape_bounds(shape: Any) -> tuple[int, int, int, int]:
    """shape의 bounding box를 EMU 단위로 반환.

    Returns:
        (left, top, width, height) 튜플 (EMU).
    """
    return shape.left, shape.top, shape.width, shape.height


def catalog_slide_shapes(slide: Any) -> list[dict[str, Any]]:
    """슬라이드의 모든 shape를 카탈로그화 (개발용 탐색 도구).

    Returns:
        [{"name": str, "shape_type": str, "has_chart": bool,
          "has_table": bool, "has_text_frame": bool,
          "left_inches": float, "top_inches": float,
          "width_inches": float, "height_inches": float}, ...]
    """
    emu_to_inches = 914400

    result = []
    for shape in slide.shapes:
        info = {
            "name": shape.name,
            "shape_type": str(shape.shape_type),
            "has_chart": shape.has_chart,
            "has_table": shape.has_table,
            "has_text_frame": shape.has_text_frame,
            "left_inches": round(shape.left / emu_to_inches, 4) if shape.left else 0,
            "top_inches": round(shape.top / emu_to_inches, 4) if shape.top else 0,
            "width_inches": round(shape.width / emu_to_inches, 4) if shape.width else 0,
            "height_inches": round(shape.height / emu_to_inches, 4) if shape.height else 0,
        }
        result.append(info)
    return result


def catalog_presentation(prs: Any) -> list[dict[str, Any]]:
    """프레젠테이션 전체 슬라이드의 shape를 카탈로그화 (개발용).

    Returns:
        [{"slide_index": int, "shapes": [...]}, ...]
    """
    return [{"slide_index": idx, "shapes": catalog_slide_shapes(slide)} for idx, slide in enumerate(prs.slides)]
