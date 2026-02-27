"""PPTX 한글 폰트 헬퍼 — a:ea (동아시아) 폰트 설정.

python-pptx의 ``run.font.name``은 ``<a:latin>`` 요소만 설정하므로,
한글 텍스트가 시스템 기본 폰트로 렌더링되는 문제가 있다.
이 모듈은 ``<a:ea>`` (East Asian) 폰트를 lxml로 직접 설정하여
PPTX에서 한글이 지정된 폰트로 정상 렌더링되도록 한다.

원본: im/src/design_renderer/pptx_engine/font_helper.py
"""

from __future__ import annotations

import logging
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)

# OOXML 네임스페이스
_nsmap = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def _qn(tag: str) -> str:
    """네임스페이스 접두사가 포함된 태그를 Clark notation으로 변환."""
    prefix, local = tag.split(":")
    return f"{{{_nsmap[prefix]}}}{local}"


def set_font_with_ea(
    run: Any,
    font_name: str,
    *,
    ea_font: str | None = None,
) -> None:
    """run에 Latin + East Asian 폰트를 동시에 설정한다.

    ``run.font.name``으로 ``<a:latin>``을 설정하고,
    lxml로 ``<a:ea>``를 직접 추가/수정한다.

    Args:
        run: pptx.text.run._Run 인스턴스.
        font_name: Latin 폰트명 (예: "SUIT Medium").
        ea_font: 동아시아 폰트명. None이면 font_name과 동일.
    """
    ea = ea_font or font_name
    run.font.name = font_name
    _set_ea_font_on_rpr(run, ea)


def _set_ea_font_on_rpr(run: Any, ea_font: str) -> None:
    """run의 rPr XML에 <a:ea> 요소를 추가/수정한다."""
    r_elem = run._r
    rpr = r_elem.find(_qn("a:rPr"))
    if rpr is None:
        rpr = etree.SubElement(r_elem, _qn("a:rPr"))
        r_elem.insert(0, rpr)

    ea_tag = _qn("a:ea")
    for existing_ea in rpr.findall(ea_tag):
        rpr.remove(existing_ea)

    ea_elem = etree.SubElement(rpr, ea_tag)
    ea_elem.set("typeface", ea_font)


def ensure_ea_fonts_on_slide(
    slide: Any,
    *,
    ea_font: str = "SUIT Medium",
    heading_ea_font: str = "SUITE",
    title_ph_idx: int = 11,
) -> int:
    """슬라이드의 모든 text run에 a:ea 폰트를 보장한다.

    이미 ``<a:ea>``가 설정된 run은 건너뛴다.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        ea_font: 본문용 동아시아 폰트명.
        heading_ea_font: 제목용 동아시아 폰트명.
        title_ph_idx: 제목 플레이스홀더 인덱스.

    Returns:
        ea 폰트가 추가된 run 수.
    """
    count = 0
    ea_tag = _qn("a:ea")

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue

        is_title = False
        try:
            ph_format = shape.placeholder_format
            if ph_format is not None and ph_format.idx == title_ph_idx:
                is_title = True
        except (ValueError, AttributeError):
            pass

        target_ea = heading_ea_font if is_title else ea_font

        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                r_elem = run._r
                rpr = r_elem.find(_qn("a:rPr"))
                if rpr is None:
                    continue
                if rpr.find(ea_tag) is not None:
                    continue

                ea_elem = etree.SubElement(rpr, ea_tag)
                ea_elem.set("typeface", target_ea)
                count += 1

    return count


def ensure_ea_fonts_on_presentation(
    prs: Any,
    *,
    ea_font: str = "SUIT Medium",
) -> int:
    """프레젠테이션 전체 슬라이드에 a:ea 폰트를 보장한다.

    Returns:
        ea 폰트가 추가된 총 run 수.
    """
    total = 0
    for slide in prs.slides:
        total += ensure_ea_fonts_on_slide(slide, ea_font=ea_font)

    if total > 0:
        logger.info("a:ea 폰트 후처리: %d개 run에 '%s' 설정 완료", total, ea_font)
    return total
