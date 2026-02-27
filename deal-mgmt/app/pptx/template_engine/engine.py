"""모듈 5: 통합 오케스트레이터 — 모듈 1~4를 통합 호출하여 템플릿 시각화를 수행.

process_template()이 메인 진입점이며,
JSON instructions에 따라 슬라이드별로 차트/테이블/이미지/텍스트를 교체한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .chart_replacer import replace_chart_data
from .constants import NUMBER_FORMAT_NEGATIVE_PARENS
from .exceptions import TemplateEngineError
from .font_helper import ensure_ea_fonts_on_presentation
from .image_placer import replace_image_in_placeholder, replace_images_in_grid
from .table_builder import replace_table_data, split_table_across_slides
from .text_replacer import (
    replace_placeholders_in_text,
    replace_text_preserving_format,
    replace_timeline_texts,
)

logger = logging.getLogger(__name__)


@dataclass
class TemplateVisualizationResult:
    """시각화 엔진 처리 결과."""

    output_path: str = ""
    charts_updated: int = 0
    tables_updated: int = 0
    images_placed: int = 0
    texts_replaced: int = 0
    slides_added: int = 0
    errors: list[str] = field(default_factory=list)


def process_template(
    template_path: str | Path,
    output_path: str | Path,
    instructions: dict[str, Any],
) -> TemplateVisualizationResult:
    """템플릿 PPTX에 시각화 데이터를 적용하여 결과 PPTX를 생성.

    Args:
        template_path: 입력 템플릿 PPTX 경로.
        output_path: 출력 PPTX 경로.
        instructions: 시각화 지시 사항.
            {
                "slides": [
                    {
                        "slide_index": 0,
                        "charts": [...],
                        "tables": [...],
                        "images": [...],
                        "texts": [...],
                    }
                ]
            }

    Returns:
        TemplateVisualizationResult.
    """
    from pptx import Presentation

    template = Path(template_path)
    if not template.exists():
        raise FileNotFoundError(f"템플릿 파일 없음: {template}")

    prs = Presentation(str(template))
    result = TemplateVisualizationResult(output_path=str(output_path))

    for slide_inst in instructions.get("slides", []):
        slide_idx = slide_inst.get("slide_index", 0)

        if slide_idx >= len(prs.slides):
            result.errors.append(f"슬라이드 인덱스 {slide_idx} 범위 초과 (총 {len(prs.slides)}개)")
            continue

        slide = prs.slides[slide_idx]

        # ── 1. 차트 교체 ──
        for chart_inst in slide_inst.get("charts", []):
            try:
                replace_chart_data(
                    slide,
                    chart_inst["shape_name"],
                    chart_inst["categories"],
                    chart_inst["series"],
                    scale_factor=chart_inst.get("scale_factor", 1.0),
                    number_format=chart_inst.get("number_format", NUMBER_FORMAT_NEGATIVE_PARENS),
                )
                result.charts_updated += 1
            except TemplateEngineError as e:
                result.errors.append(f"차트 오류 [{chart_inst.get('shape_name', '?')}]: {e}")

        # ── 2. 테이블 교체 ──
        for table_inst in slide_inst.get("tables", []):
            try:
                if table_inst.get("split_across_slides"):
                    added = split_table_across_slides(
                        prs,
                        slide_idx,
                        table_inst["shape_name"],
                        table_inst.get("headers"),
                        table_inst["rows"],
                        max_rows_per_slide=table_inst.get("max_rows", 20),
                    )
                    result.slides_added += added - 1
                else:
                    replace_table_data(
                        slide,
                        table_inst["shape_name"],
                        table_inst.get("headers"),
                        table_inst["rows"],
                    )
                result.tables_updated += 1
            except TemplateEngineError as e:
                result.errors.append(f"테이블 오류 [{table_inst.get('shape_name', '?')}]: {e}")

        # ── 3. 이미지 교체 ──
        for image_inst in slide_inst.get("images", []):
            try:
                if image_inst.get("grid_prefix"):
                    sources = image_inst.get("sources_base64", [])
                    pics = replace_images_in_grid(slide, image_inst["grid_prefix"], sources)
                    result.images_placed += len(pics)
                else:
                    source = image_inst.get("source_base64", "")
                    replace_image_in_placeholder(slide, image_inst["shape_name"], source)
                    result.images_placed += 1
            except TemplateEngineError as e:
                result.errors.append(f"이미지 오류 [{image_inst.get('shape_name', '?')}]: {e}")

        # ── 4. 텍스트 교체 ──
        for text_inst in slide_inst.get("texts", []):
            try:
                mode = text_inst.get("mode", "replace")

                if mode == "placeholder":
                    replace_placeholders_in_text(
                        slide,
                        text_inst["shape_name"],
                        text_inst["replacements"],
                    )
                elif mode == "timeline":
                    replace_timeline_texts(
                        slide,
                        text_inst["prefix"],
                        text_inst["items"],
                    )
                else:  # mode == "replace"
                    replace_text_preserving_format(
                        slide,
                        text_inst["shape_name"],
                        text_inst["texts"],
                    )
                result.texts_replaced += 1
            except TemplateEngineError as e:
                result.errors.append(f"텍스트 오류 [{text_inst.get('shape_name', text_inst.get('prefix', '?'))}]: {e}")

    # ── 한글 폰트 후처리 ──
    ensure_ea_fonts_on_presentation(prs, ea_font="SUIT Medium")

    # ── 저장 ──
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))

    logger.info(
        "템플릿 시각화 완료: 차트 %d, 테이블 %d, 이미지 %d, 텍스트 %d (오류 %d)",
        result.charts_updated,
        result.tables_updated,
        result.images_placed,
        result.texts_replaced,
        len(result.errors),
    )

    return result
