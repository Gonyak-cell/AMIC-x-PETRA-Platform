"""AMIC IM PPTX 마스터 템플릿 생성 스크립트.

TITAN PPTX에서 SL Template의 슬라이드 마스터/레이아웃을 추출하고,
AMIC 디자인(폰트/컬러)을 적용하여 amic_im_template.pptx를 생성한다.

사용법:
    python -m src.design_renderer.pptx_engine.create_template

또는 프로그래밍 방식:
    from src.design_renderer.pptx_engine.create_template import create_im_template
    create_im_template()
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

logger = logging.getLogger(__name__)

# 경로 상수
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # auto-im-generator/
_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_TEMPLATE_OUTPUT = _ASSETS_DIR / "templates" / "amic_im_template.pptx"

# TITAN PPTX 경로 (sample IM)
_SAMPLE_IM_DIR = _PROJECT_ROOT.parent / "sample IM"
_TITAN_PPTX = _SAMPLE_IM_DIR / "TITAN - IM - vF 251201.pptx"


def create_im_template(
    *,
    source_pptx: Path | None = None,
    output_path: Path | None = None,
    tokens: IMDesignTokens | None = None,
) -> Path:
    """AMIC IM PPTX 마스터 템플릿 생성.

    접근법:
    1. 새 프레젠테이션을 처음부터 생성
    2. 슬라이드 크기 설정 (10.83" x 7.5")
    3. 3개 레이아웃 구성 (COVER, BLANK, MAIN)
    4. 테마 폰트/컬러 설정

    Args:
        source_pptx: 소스 TITAN PPTX (참조용, 현재 미사용).
        output_path: 출력 경로. None이면 기본 위치.
        tokens: 디자인 토큰.

    Returns:
        생성된 템플릿 파일 경로.
    """
    if tokens is None:
        tokens = DEFAULT_TOKENS

    out = output_path or _TEMPLATE_OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()

    # 슬라이드 크기 설정
    prs.slide_width = Inches(tokens.layout.page_width)  # 10.83"
    prs.slide_height = Inches(tokens.layout.page_height)  # 7.5"

    # 테마 폰트 설정
    _set_theme_fonts(prs, tokens)

    # 테마 컬러 설정
    _set_theme_colors(prs, tokens)

    # 기본 레이아웃 이름 변경 및 정리
    _configure_layouts(prs, tokens)

    prs.save(str(out))
    logger.info(f"AMIC IM 마스터 템플릿 생성: {out}")
    return out


# ---------------------------------------------------------------------------
# 테마 폰트 설정
# ---------------------------------------------------------------------------


def _set_theme_fonts(prs: Presentation, tokens: IMDesignTokens) -> None:
    """테마 폰트를 AMIC 폰트로 교체.

    Major (제목): Inter
    Minor (본문): Pretendard
    """
    slide_master = prs.slide_masters[0]
    theme = slide_master.element.find(qn("p:txStyles"))

    # python-pptx에서 직접 접근이 제한적이므로 XML 레벨 수정
    # Theme XML 접근
    theme_part = prs.slide_masters[0].part
    if hasattr(theme_part, "slide_master"):
        pass  # python-pptx 내부 구조

    # theme.xml 직접 수정
    try:
        theme_xml = prs.slide_masters[0].element
        # majorFont, minorFont 속성 찾기
        for font_scheme in theme_xml.iter(qn("a:majorFont")):
            latin = font_scheme.find(qn("a:latin"))
            if latin is not None:
                latin.set("typeface", tokens.typography.font_heading)

        for font_scheme in theme_xml.iter(qn("a:minorFont")):
            latin = font_scheme.find(qn("a:latin"))
            if latin is not None:
                latin.set("typeface", tokens.typography.font_body)
    except Exception as e:
        logger.warning(f"테마 폰트 설정 실패, 기본 폰트 유지: {e}")


# ---------------------------------------------------------------------------
# 테마 컬러 설정
# ---------------------------------------------------------------------------


def _set_theme_colors(prs: Presentation, tokens: IMDesignTokens) -> None:
    """테마 컬러를 AMIC 컬러로 교체.

    dk1 (dark 1): AMIC Dark Green #0F3A32
    accent1: AMIC Green #26C260
    """
    c = tokens.colors
    color_map = {
        "dk1": c.primary,        # #0F3A32
        "accent1": c.accent,     # #26C260
        "accent2": c.positive,   # #26C260
        "accent3": c.caution,    # #EF6C00
        "accent4": c.negative,   # #BC2C1A
    }

    try:
        theme_xml = prs.slide_masters[0].element
        for clr_scheme in theme_xml.iter(qn("a:clrScheme")):
            for tag_name, hex_color in color_map.items():
                elem = clr_scheme.find(qn(f"a:{tag_name}"))
                if elem is not None:
                    srgb = elem.find(qn("a:srgbClr"))
                    if srgb is not None:
                        srgb.set("val", hex_color.lstrip("#"))
                    else:
                        # srgbClr 요소 생성
                        for child in list(elem):
                            elem.remove(child)
                        from lxml import etree

                        new_srgb = etree.SubElement(elem, qn("a:srgbClr"))
                        new_srgb.set("val", hex_color.lstrip("#"))
    except Exception as e:
        logger.warning(f"테마 컬러 설정 실패: {e}")


# ---------------------------------------------------------------------------
# 레이아웃 구성
# ---------------------------------------------------------------------------


def _configure_layouts(prs: Presentation, tokens: IMDesignTokens) -> None:
    """기본 레이아웃을 AMIC IM 용으로 구성.

    python-pptx 기본 프레젠테이션은 여러 기본 레이아웃을 포함한다.
    COVER(0), BLANK(6), MAIN(5 or custom) 패턴으로 매핑.
    """
    slide_master = prs.slide_masters[0]
    layouts = slide_master.slide_layouts

    # 기본 레이아웃 정보 로깅
    layout_count = len(layouts)
    logger.info(f"기본 레이아웃 {layout_count}개 발견")

    # 레이아웃 이름 매핑 (python-pptx 기본 레이아웃)
    # Index 0: Title Slide (→ COVER로 사용)
    # Index 5: Title Only (→ MAIN으로 사용, 제목 ph만 있음)
    # Index 6: Blank (→ BLANK로 사용)

    # MAIN 레이아웃 (Title Only)에 각주/페이지번호 플레이스홀더 추가
    if layout_count > 5:
        main_layout = layouts[5]  # Title Only
        _add_footer_placeholders(main_layout, tokens)

    # COVER 레이아웃 (index 0) — 기본 Title Slide 그대로 활용


def _add_footer_placeholders(layout: Any, tokens: IMDesignTokens) -> None:
    """MAIN 레이아웃에 각주(idx=12)와 페이지번호(idx=13) 플레이스홀더 추가.

    python-pptx는 커스텀 플레이스홀더 생성을 직접 지원하지 않으므로
    XML 레벨에서 추가한다.
    """
    from lxml import etree

    lay = tokens.layout

    # 각주 플레이스홀더 (idx=12)
    _add_placeholder_xml(
        layout,
        idx=lay.ph_footnote_idx,
        left=Inches(lay.margin_left),
        top=Inches(6.85),
        width=Inches(7.83),
        height=Inches(0.4),
        font_size=tokens.font_sizes.footnote,
        ph_type="body",
    )

    # 페이지번호 플레이스홀더 (idx=13)
    _add_placeholder_xml(
        layout,
        idx=lay.ph_page_number_idx,
        left=Inches(9.83),
        top=Inches(6.85),
        width=Inches(0.5),
        height=Inches(0.4),
        font_size=tokens.font_sizes.page_number,
        ph_type="sldNum",
    )


def _add_placeholder_xml(
    layout: Any,
    *,
    idx: int,
    left: int,
    top: int,
    width: int,
    height: int,
    font_size: int = 10,
    ph_type: str = "body",
) -> None:
    """레이아웃에 플레이스홀더 shape XML 추가."""
    from lxml import etree

    sp_tree = layout.element.find(qn("p:cSld")).find(qn("p:spTree"))

    # <p:sp> 요소 생성
    sp = etree.SubElement(sp_tree, qn("p:sp"))

    # nvSpPr (non-visual shape properties)
    nv_sp_pr = etree.SubElement(sp, qn("p:nvSpPr"))
    c_nv_pr = etree.SubElement(nv_sp_pr, qn("p:cNvPr"))
    c_nv_pr.set("id", str(idx + 100))  # 유니크 ID
    c_nv_pr.set("name", f"Placeholder {idx}")

    c_nv_sp_pr = etree.SubElement(nv_sp_pr, qn("p:cNvSpPr"))
    sp_locks = etree.SubElement(c_nv_sp_pr, qn("a:spLocks"))
    sp_locks.set("noGrp", "1")

    nv_pr = etree.SubElement(nv_sp_pr, qn("p:nvPr"))
    ph = etree.SubElement(nv_pr, qn("p:ph"))
    ph.set("type", ph_type)
    ph.set("idx", str(idx))

    # spPr (shape properties - position/size)
    sp_pr = etree.SubElement(sp, qn("p:spPr"))
    xfrm = etree.SubElement(sp_pr, qn("a:xfrm"))
    off = etree.SubElement(xfrm, qn("a:off"))
    off.set("x", str(left))
    off.set("y", str(top))
    ext = etree.SubElement(xfrm, qn("a:ext"))
    ext.set("cx", str(width))
    ext.set("cy", str(height))

    # txBody (text body with default font)
    tx_body = etree.SubElement(sp, qn("p:txBody"))
    body_pr = etree.SubElement(tx_body, qn("a:bodyPr"))
    lst_style = etree.SubElement(tx_body, qn("a:lstStyle"))
    p_elem = etree.SubElement(tx_body, qn("a:p"))
    end_para_rpr = etree.SubElement(p_elem, qn("a:endParaRPr"))
    end_para_rpr.set("lang", "ko-KR")
    end_para_rpr.set("sz", str(font_size * 100))  # hundredths of a point


# ---------------------------------------------------------------------------
# Layout 헬퍼 함수 (외부에서 사용)
# ---------------------------------------------------------------------------


def get_layout_by_purpose(prs: Presentation, purpose: str) -> Any:
    """목적에 따른 레이아웃 반환.

    Args:
        prs: Presentation 객체.
        purpose: "cover" | "blank" | "main"

    Returns:
        SlideLayout 객체.
    """
    layouts = prs.slide_masters[0].slide_layouts
    layout_count = len(layouts)

    if purpose == "cover":
        return layouts[0]  # Title Slide
    elif purpose == "blank":
        return layouts[6] if layout_count > 6 else layouts[-1]  # Blank
    elif purpose == "main":
        return layouts[5] if layout_count > 5 else layouts[1]  # Title Only
    else:
        raise ValueError(f"Unknown layout purpose: {purpose}")


# ---------------------------------------------------------------------------
# 스크립트 실행
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = create_im_template()
    print(f"Template created: {path}")
