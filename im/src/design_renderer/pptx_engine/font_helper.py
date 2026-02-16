"""PPTX 한글 폰트 헬퍼 — a:ea (동아시아) 폰트 설정.

> 마지막 수정: 2026-02-11 10:00:00

python-pptx의 ``run.font.name``은 ``<a:latin>`` 요소만 설정하므로,
한글 텍스트가 시스템 기본 폰트로 렌더링되는 문제가 있다.
이 모듈은 ``<a:ea>`` (East Asian) 폰트를 lxml로 직접 설정하여
PPTX에서 한글이 지정된 폰트로 정상 렌더링되도록 한다.

Usage::

    from src.design_renderer.pptx_engine.font_helper import (
        set_font_with_ea,
        ensure_ea_fonts_on_slide,
    )

    # 개별 run에 한글 폰트 설정
    set_font_with_ea(run, "Pretendard")

    # 슬라이드 전체 후처리
    ensure_ea_fonts_on_slide(slide, ea_font="Pretendard")
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
    """네임스페이스 접두사가 포함된 태그를 Clark notation으로 변환.

    Args:
        tag: "a:ea" 같은 네임스페이스:태그 문자열.

    Returns:
        "{http://...}ea" 형식의 Clark notation.
    """
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
        font_name: Latin 폰트명 (예: "Pretendard", "Inter").
        ea_font: 동아시아 폰트명. None이면 font_name과 동일하게 설정.
    """
    ea = ea_font or font_name

    # Latin 폰트 설정 (기존 python-pptx API)
    run.font.name = font_name

    # East Asian 폰트 설정 (lxml 직접 조작)
    _set_ea_font_on_rpr(run, ea)


def _set_ea_font_on_rpr(run: Any, ea_font: str) -> None:
    """run의 rPr XML에 <a:ea> 요소를 추가/수정한다.

    Args:
        run: pptx.text.run._Run 인스턴스.
        ea_font: 동아시아 폰트명.
    """
    # rPr (run properties) 요소 가져오기/생성
    r_elem = run._r
    rpr = r_elem.find(_qn("a:rPr"))
    if rpr is None:
        rpr = etree.SubElement(r_elem, _qn("a:rPr"))
        # rPr은 r의 첫 번째 자식이어야 함
        r_elem.insert(0, rpr)

    # 기존 a:ea 제거 후 새로 추가
    ea_tag = _qn("a:ea")
    for existing_ea in rpr.findall(ea_tag):
        rpr.remove(existing_ea)

    ea_elem = etree.SubElement(rpr, ea_tag)
    ea_elem.set("typeface", ea_font)


def ensure_ea_fonts_on_slide(
    slide: Any,
    *,
    ea_font: str = "Pretendard",
) -> int:
    """슬라이드의 모든 text run에 a:ea 폰트를 보장한다.

    이미 ``<a:ea>``가 설정된 run은 건너뛴다 (기존 설정 유지).
    ``<a:ea>``가 없는 run에만 지정된 ea_font를 추가한다.

    Args:
        slide: pptx.slide.Slide 인스턴스.
        ea_font: 설정할 동아시아 폰트명.

    Returns:
        ea 폰트가 추가된 run 수.
    """
    count = 0
    ea_tag = _qn("a:ea")

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                r_elem = run._r
                rpr = r_elem.find(_qn("a:rPr"))
                if rpr is None:
                    continue

                # 이미 a:ea가 있으면 스킵
                if rpr.find(ea_tag) is not None:
                    continue

                ea_elem = etree.SubElement(rpr, ea_tag)
                ea_elem.set("typeface", ea_font)
                count += 1

    return count


def ensure_ea_fonts_on_presentation(
    prs: Any,
    *,
    ea_font: str = "Pretendard",
) -> int:
    """프레젠테이션 전체 슬라이드에 a:ea 폰트를 보장한다.

    Args:
        prs: pptx.presentation.Presentation 인스턴스.
        ea_font: 설정할 동아시아 폰트명.

    Returns:
        ea 폰트가 추가된 총 run 수.
    """
    total = 0
    for slide in prs.slides:
        total += ensure_ea_fonts_on_slide(slide, ea_font=ea_font)

    if total > 0:
        logger.info(f"a:ea 폰트 후처리: {total}개 run에 '{ea_font}' 설정 완료")
    return total
