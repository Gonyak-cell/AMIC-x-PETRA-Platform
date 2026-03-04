"""AMIC IM PPTX 마스터 템플릿 생성 스크립트.

5종 레이아웃(BLANK, FOREST, BLANK_PGNO, MAIN, MAIN_w/Andersen)을 구성하고,
AMIC 디자인 토큰(폰트/컬러/플레이스홀더)을 적용하여 amic_im_template.pptx를 생성.

레이아웃 매핑:
  - BLANK (idx 6)       : 완전 빈 슬라이드 (disclaimer 등)
  - FOREST (idx 0)      : 배경 이미지 슬라이드 (cover, TOC 간지, contact)
  - BLANK_PGNO (idx 1)  : 페이지 번호만 (재무제표 full-width)
  - MAIN (idx 5)        : 제목바 + 각주 + 페이지번호 (일반 콘텐츠)
  - MAIN_w/Andersen (idx 2) : MAIN + 공동 브랜딩

사용법:
    python -m src.design_renderer.pptx_engine.create_template

또는 프로그래밍 방식:
    from src.design_renderer.pptx_engine.create_template import create_im_template
    create_im_template()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Inches

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

logger = logging.getLogger(__name__)

# 경로 상수
_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_TEMPLATE_OUTPUT = _ASSETS_DIR / "templates" / "amic_im_template.pptx"

# ---------------------------------------------------------------------------
# 레이아웃 이름 상수
# ---------------------------------------------------------------------------

LAYOUT_BLANK = "BLANK"
LAYOUT_FOREST = "FOREST"
LAYOUT_BLANK_PGNO = "BLANK_PGNO"
LAYOUT_MAIN = "MAIN"
LAYOUT_MAIN_ANDERSEN = "MAIN_w/Andersen"

# python-pptx 기본 레이아웃 인덱스 → 목적 매핑
# 0: Title Slide → FOREST
# 1: Title and Content → BLANK_PGNO
# 2: Section Header → MAIN_w/Andersen
# 5: Title Only → MAIN
# 6: Blank → BLANK
_PURPOSE_TO_INDEX = {
    "blank": 6,
    "forest": 0,
    "cover": 0,  # alias
    "blank_pgno": 1,
    "main": 5,
    "main_andersen": 2,
}


def create_im_template(
    *,
    output_path: Path | None = None,
    tokens: IMDesignTokens | None = None,
) -> Path:
    """AMIC IM PPTX 마스터 템플릿 생성.

    5종 레이아웃을 구성하고 테마 폰트/컬러를 설정한다.

    Args:
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

    # 레이아웃 구성 (5종)
    _configure_layouts(prs, tokens)

    prs.save(str(out))
    logger.info(f"AMIC IM 마스터 템플릿 생성: {out} (5종 레이아웃)")
    return out


# ---------------------------------------------------------------------------
# 테마 폰트 설정
# ---------------------------------------------------------------------------


def _set_theme_fonts(prs: Presentation, tokens: IMDesignTokens) -> None:
    """테마 폰트를 AMIC 폰트로 교체."""
    try:
        theme_xml = prs.slide_masters[0].element
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
    """테마 컬러를 AMIC 컬러로 교체."""
    c = tokens.colors
    color_map = {
        "dk1": c.primary,  # #0F3A32
        "accent1": c.accent,  # #26C260
        "accent2": c.positive,  # #26C260
        "accent3": c.caution,  # #EF6C00
        "accent4": c.negative,  # #BC2C1A
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
                        for child in list(elem):
                            elem.remove(child)
                        from lxml import etree

                        new_srgb = etree.SubElement(elem, qn("a:srgbClr"))
                        new_srgb.set("val", hex_color.lstrip("#"))
    except Exception as e:
        logger.warning(f"테마 컬러 설정 실패: {e}")


# ---------------------------------------------------------------------------
# 레이아웃 구성 (5종)
# ---------------------------------------------------------------------------


def _configure_layouts(prs: Presentation, tokens: IMDesignTokens) -> None:
    """5종 레이아웃 구성.

    python-pptx 기본 레이아웃을 재활용하여 5종으로 매핑:
    - BLANK (idx 6): 빈 슬라이드
    - FOREST (idx 0): 커버/간지용 (배경은 슬라이드 생성 시 적용)
    - BLANK_PGNO (idx 1): 페이지 번호만
    - MAIN (idx 5): 제목 + 각주 + 페이지번호
    - MAIN_w/Andersen (idx 2): 공동 브랜딩
    """
    slide_master = prs.slide_masters[0]
    layouts = slide_master.slide_layouts
    layout_count = len(layouts)
    logger.info(f"기본 레이아웃 {layout_count}개 발견, 5종 구성 시작")

    # MAIN 레이아웃 (Title Only, idx=5) — 각주/페이지번호 플레이스홀더 추가
    if layout_count > 5:
        main_layout = layouts[5]
        _add_footer_placeholders(main_layout, tokens)

    # BLANK_PGNO 레이아웃 (idx=1) — 페이지번호만
    if layout_count > 1:
        blank_pgno_layout = layouts[1]
        _add_page_number_placeholder(blank_pgno_layout, tokens)

    # MAIN_w/Andersen (idx=2) — 각주/페이지번호 + 로고 영역
    if layout_count > 2:
        andersen_layout = layouts[2]
        _add_footer_placeholders(andersen_layout, tokens)


def _add_footer_placeholders(layout: Any, tokens: IMDesignTokens) -> None:
    """MAIN 레이아웃에 각주(idx=12)와 페이지번호(idx=13) 플레이스홀더 추가."""
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


def _add_page_number_placeholder(layout: Any, tokens: IMDesignTokens) -> None:
    """BLANK_PGNO 레이아웃에 페이지번호(idx=13)만 추가."""
    lay = tokens.layout

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

    sp = etree.SubElement(sp_tree, qn("p:sp"))

    nv_sp_pr = etree.SubElement(sp, qn("p:nvSpPr"))
    c_nv_pr = etree.SubElement(nv_sp_pr, qn("p:cNvPr"))
    c_nv_pr.set("id", str(idx + 100))
    c_nv_pr.set("name", f"Placeholder {idx}")

    c_nv_sp_pr = etree.SubElement(nv_sp_pr, qn("p:cNvSpPr"))
    sp_locks = etree.SubElement(c_nv_sp_pr, qn("a:spLocks"))
    sp_locks.set("noGrp", "1")

    nv_pr = etree.SubElement(nv_sp_pr, qn("p:nvPr"))
    ph = etree.SubElement(nv_pr, qn("p:ph"))
    ph.set("type", ph_type)
    ph.set("idx", str(idx))

    sp_pr = etree.SubElement(sp, qn("p:spPr"))
    xfrm = etree.SubElement(sp_pr, qn("a:xfrm"))
    off = etree.SubElement(xfrm, qn("a:off"))
    off.set("x", str(left))
    off.set("y", str(top))
    ext = etree.SubElement(xfrm, qn("a:ext"))
    ext.set("cx", str(width))
    ext.set("cy", str(height))

    tx_body = etree.SubElement(sp, qn("p:txBody"))
    etree.SubElement(tx_body, qn("a:bodyPr"))
    etree.SubElement(tx_body, qn("a:lstStyle"))
    p_elem = etree.SubElement(tx_body, qn("a:p"))
    end_para_rpr = etree.SubElement(p_elem, qn("a:endParaRPr"))
    end_para_rpr.set("lang", "ko-KR")
    end_para_rpr.set("sz", str(font_size * 100))


# ---------------------------------------------------------------------------
# Layout 헬퍼 함수 (외부에서 사용)
# ---------------------------------------------------------------------------


def get_layout_by_purpose(prs: Presentation, purpose: str) -> Any:
    """목적에 따른 레이아웃 반환.

    5종 레이아웃 매핑:
    - "blank"         → Blank (idx 6)
    - "forest"/"cover"→ Title Slide (idx 0) — 배경은 슬라이드 생성 시 적용
    - "blank_pgno"    → Title and Content (idx 1) — 페이지번호 플레이스홀더
    - "main"          → Title Only (idx 5) — 제목+각주+페이지번호
    - "main_andersen"  → Section Header (idx 2) — 공동 브랜딩

    Args:
        prs: Presentation 객체.
        purpose: 레이아웃 목적 식별자.

    Returns:
        SlideLayout 객체.

    Raises:
        ValueError: 알 수 없는 purpose.
    """
    layouts = prs.slide_masters[0].slide_layouts
    layout_count = len(layouts)

    idx = _PURPOSE_TO_INDEX.get(purpose)
    if idx is None:
        raise ValueError(
            f"Unknown layout purpose: '{purpose}'. "
            f"Valid: {list(_PURPOSE_TO_INDEX.keys())}"
        )

    if idx >= layout_count:
        # 폴백: 지원하지 않는 인덱스면 Blank 사용
        logger.warning(
            f"레이아웃 인덱스 {idx} ('{purpose}') 없음, "
            f"Blank 폴백 (layout_count={layout_count})"
        )
        return layouts[min(6, layout_count - 1)]

    return layouts[idx]


# ---------------------------------------------------------------------------
# 스크립트 실행
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = create_im_template()
    print(f"Template created: {path}")
