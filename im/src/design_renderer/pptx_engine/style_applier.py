"""AMIC 폰트/컬러 일괄 적용 + 보안 — 스타일 표준화 및 편집 제한/워터마크.

Presentation 전체 또는 개별 슬라이드의 텍스트 run에
AMIC 디자인 토큰 기반 폰트/컬러를 일괄 적용한다.
편집 제한 모드와 반투명 워터마크 기능도 제공한다.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Any

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Run-level 스타일 적용
# ---------------------------------------------------------------------------


def apply_run_style(
    run: Any,
    *,
    font_name: str | None = None,
    font_size: int | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    color_hex: str | None = None,
) -> None:
    """개별 run에 폰트/컬러 스타일 적용.

    Args:
        run: pptx.text.text.Run 인스턴스.
        font_name: 폰트명. None이면 변경 안 함.
        font_size: 폰트 크기 (pt). None이면 변경 안 함.
        bold: Bold 여부. None이면 변경 안 함.
        italic: Italic 여부. None이면 변경 안 함.
        color_hex: 컬러 hex (예: "#0F3A32"). None이면 변경 안 함.
    """
    font = run.font
    if font_name is not None:
        font.name = font_name
    if font_size is not None:
        font.size = Pt(font_size)
    if bold is not None:
        font.bold = bold
    if italic is not None:
        font.italic = italic
    if color_hex is not None:
        font.color.rgb = RGBColor.from_string(color_hex.lstrip("#"))


def apply_paragraph_style(
    paragraph: Any,
    *,
    font_name: str | None = None,
    font_size: int | None = None,
    bold: bool | None = None,
    color_hex: str | None = None,
) -> None:
    """paragraph 내 모든 run에 스타일 적용.

    Args:
        paragraph: pptx.text.text._Paragraph 인스턴스.
        font_name, font_size, bold, color_hex: 적용할 스타일.
    """
    for run in paragraph.runs:
        apply_run_style(
            run,
            font_name=font_name,
            font_size=font_size,
            bold=bold,
            color_hex=color_hex,
        )


# ---------------------------------------------------------------------------
# 슬라이드 단위 스타일 적용
# ---------------------------------------------------------------------------


def apply_slide_style(
    slide: Any,
    *,
    tokens: IMDesignTokens | None = None,
    skip_placeholders: bool = False,
) -> None:
    """슬라이드 내 모든 텍스트 shape에 AMIC 스타일 적용.

    - 제목 (idx=11): SUITE, 16pt, Bold, primary
    - 각주 (idx=12): Pretendard, 9pt, text_secondary
    - 페이지번호 (idx=13): Pretendard, 10pt, text_secondary
    - 기타 shape: Pretendard, body 색상

    Args:
        slide: Slide 객체.
        tokens: 디자인 토큰.
        skip_placeholders: True이면 플레이스홀더 텍스트는 건드리지 않음.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    t = tokens.typography
    c = tokens.colors
    f = tokens.font_sizes

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue

        # 플레이스홀더 특수 처리
        # python-pptx raises ValueError for non-placeholder shapes
        try:
            ph_format = shape.placeholder_format
        except ValueError:
            ph_format = None

        if ph_format is not None:
            if skip_placeholders:
                continue
            idx = ph_format.idx
            if idx == tokens.layout.ph_title_idx:
                _apply_to_text_frame(
                    shape.text_frame,
                    font_name=t.font_heading,
                    font_size=f.slide_title,
                    bold=True,
                    color_hex=c.primary,
                )
                continue
            if idx == tokens.layout.ph_footnote_idx:
                _apply_to_text_frame(
                    shape.text_frame,
                    font_name=t.font_body,
                    font_size=f.footnote,
                    color_hex=c.text_secondary,
                )
                continue
            if idx == tokens.layout.ph_page_number_idx:
                _apply_to_text_frame(
                    shape.text_frame,
                    font_name=t.font_mono,
                    font_size=f.page_number,
                    color_hex=c.text_secondary,
                )
                continue

        # 일반 shape: 본문 기본 스타일
        _apply_to_text_frame(
            shape.text_frame,
            font_name=t.font_body,
            color_hex=c.text_body,
        )


def _apply_to_text_frame(
    text_frame: Any,
    *,
    font_name: str | None = None,
    font_size: int | None = None,
    bold: bool | None = None,
    color_hex: str | None = None,
) -> None:
    """TextFrame 내 모든 paragraph/run에 스타일 적용."""
    for para in text_frame.paragraphs:
        for run in para.runs:
            apply_run_style(
                run,
                font_name=font_name,
                font_size=font_size,
                bold=bold,
                color_hex=color_hex,
            )


# ---------------------------------------------------------------------------
# Presentation 전체 스타일 적용
# ---------------------------------------------------------------------------


def apply_presentation_style(
    prs: Any,
    *,
    tokens: IMDesignTokens | None = None,
) -> None:
    """Presentation 전체 슬라이드에 AMIC 스타일 일괄 적용.

    모든 슬라이드의 텍스트를 순회하며 AMIC 폰트/컬러를 적용한다.

    Args:
        prs: Presentation 객체.
        tokens: 디자인 토큰.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    for slide in prs.slides:
        apply_slide_style(slide, tokens=tokens)

    logger.info(f"AMIC 스타일 적용 완료: {len(prs.slides)}개 슬라이드")


# ---------------------------------------------------------------------------
# 편집 제한 모드
# ---------------------------------------------------------------------------


def set_edit_restriction(
    prs: Any,
    *,
    read_only: bool = False,
    password: str | None = None,
) -> None:
    """PPTX 편집 제한 모드 설정.

    XML 레벨에서 p:modifyVerifier를 추가하여
    편집 제한 (수정 시 암호 요구)을 설정한다.

    Args:
        prs: Presentation 객체.
        read_only: True이면 읽기 전용 권장 모드 (약한 보호).
        password: 편집 비밀번호 (평문). SHA-512 해싱 후 적용.
    """
    if not read_only and not password:
        return

    try:
        prs_elem = prs.element
        modify_verifier = prs_elem.find(qn("p:modifyVerifier"))
        if modify_verifier is None:
            modify_verifier = etree.SubElement(prs_elem, qn("p:modifyVerifier"))

        if password:
            # OOXML 스펙: SHA-512 + salt, 100000 iterations
            salt = os.urandom(16)
            salt_b64 = base64.b64encode(salt).decode("ascii")

            pw_bytes = password.encode("utf-16-le")
            h = hashlib.sha512(salt + pw_bytes).digest()

            spin_count = 100000
            for i in range(spin_count):
                h = hashlib.sha512(i.to_bytes(4, byteorder="little") + h).digest()

            hash_b64 = base64.b64encode(h).decode("ascii")

            modify_verifier.set("cryptProviderType", "rsaAES")
            modify_verifier.set("cryptAlgorithmClass", "hash")
            modify_verifier.set("cryptAlgorithmType", "typeAny")
            modify_verifier.set("cryptAlgorithmSid", "14")  # SHA-512
            modify_verifier.set("spinCount", str(spin_count))
            modify_verifier.set("saltData", salt_b64)
            modify_verifier.set("hashData", hash_b64)
        else:
            # 간단한 읽기 전용 권장 (PowerPoint에서 편집 시 경고)
            modify_verifier.set("cryptProviderType", "none")
            modify_verifier.set("cryptAlgorithmSid", "0")
            modify_verifier.set("spinCount", "0")
            modify_verifier.set("saltData", "")
            modify_verifier.set("hashData", "")

        logger.info("PPTX 편집 제한 설정 완료")
    except Exception as e:
        logger.warning(f"편집 제한 설정 실패: {e}")


# ---------------------------------------------------------------------------
# 워터마크
# ---------------------------------------------------------------------------


def add_watermark(
    prs: Any,
    text: str = "CONFIDENTIAL",
    *,
    opacity: float = 0.2,
    color_hex: str = "#CCCCCC",
    font_size: int = 60,
    skip_first_slide: bool = True,
    tokens: IMDesignTokens | None = None,
) -> None:
    """모든 슬라이드에 반투명 대각선 워터마크 텍스트 추가.

    각 슬라이드 중앙에 45도 회전된 반투명 텍스트를 배치한다.
    모든 콘텐츠 위에 표시된다.

    Args:
        prs: Presentation 객체.
        text: 워터마크 텍스트.
        opacity: 불투명도 (0.0~1.0).
        color_hex: 워터마크 색상 (hex).
        font_size: 폰트 크기 (pt).
        skip_first_slide: True이면 표지(첫 슬라이드) 제외.
        tokens: 디자인 토큰 (페이지 치수 참조).
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    lay = tokens.layout

    shape_width = Inches(lay.page_width * 0.9)
    shape_height = Inches(1.5)
    center_x = Inches(lay.page_width / 2) - shape_width // 2
    center_y = Inches(lay.page_height / 2) - shape_height // 2

    # alpha: 100000 = 완전 불투명, 0 = 완전 투명
    alpha_val = int((1.0 - opacity) * 100000)

    for i, slide in enumerate(prs.slides):
        if skip_first_slide and i == 0:
            continue

        txBox = slide.shapes.add_textbox(center_x, center_y, shape_width, shape_height)
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = text
        run.font.size = Pt(font_size)
        run.font.name = "SUITE"
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string(color_hex.lstrip("#"))

        # solidFill에 alpha 적용 (반투명)
        rPr = run._r.get_or_add_rPr()
        solidFill = rPr.find(qn("a:solidFill"))
        if solidFill is not None:
            srgbClr = solidFill.find(qn("a:srgbClr"))
            if srgbClr is not None:
                alpha_elem = etree.SubElement(srgbClr, qn("a:alpha"))
                alpha_elem.set("val", str(alpha_val))

        # 45도 반시계 방향 회전
        txBox.rotation = -45.0

    count = len(prs.slides) - (1 if skip_first_slide else 0)
    logger.info(f"워터마크 적용 완료: '{text}', {count}개 슬라이드")
