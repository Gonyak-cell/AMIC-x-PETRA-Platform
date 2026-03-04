"""지배구조도/조직도 생성 — chart_engine 위임 어댑터.

> 마지막 수정: 2026-02-10 13:45:13

IMDocumentData.org_structure 데이터를 Graphviz 그래프로 변환하여
PPTX (PNG 삽입) 및 PDF (SVG 인라인) 듀얼 출력을 지원한다.
실제 그래프 생성은 chart_engine.graphviz에 위임.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from src.chart_engine.config import chart_config_from_design_tokens
from src.chart_engine.export.svg_exporter import graphviz_to_svg as _ce_graphviz_to_svg
from src.chart_engine.graphviz.org_chart import create_org_chart as _ce_create_org_chart
from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens

logger = logging.getLogger(__name__)


def _tokens_to_config(tokens: IMDesignTokens | None = None) -> "ChartConfig":  # noqa: F821
    """IMDesignTokens → ChartConfig (chart_engine 공통 어댑터 위임)."""
    tokens = tokens or DEFAULT_TOKENS
    return chart_config_from_design_tokens(tokens)


def create_org_chart(
    structure: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
    rankdir: str = "TB",
) -> Any:
    """조직도 Graphviz Digraph 생성 (chart_engine 위임)."""
    return _ce_create_org_chart(
        structure, title=title, config=_tokens_to_config(tokens), rankdir=rankdir
    )


# ---------------------------------------------------------------------------
# PPTX 삽입 (PNG)
# ---------------------------------------------------------------------------


def render_org_chart_pptx(
    slide: Any,
    structure: dict[str, Any],
    *,
    left: float = 0.5,
    top: float = 1.5,
    width: float = 9.0,
    height: float = 4.5,
    title: str = "",
    tokens: IMDesignTokens | None = None,
) -> None:
    """조직도를 PNG로 렌더링하여 PPTX 슬라이드에 삽입."""
    from pptx.util import Inches

    dot = create_org_chart(structure, title=title, tokens=tokens)
    dot.format = "png"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "org_chart"
        dot.render(filename=str(output_path), cleanup=True)
        png_path = Path(f"{output_path}.png")

        if png_path.exists():
            slide.shapes.add_picture(
                str(png_path),
                Inches(left),
                Inches(top),
                Inches(width),
                Inches(height),
            )
        else:
            logger.warning("조직도 PNG 생성 실패")


# ---------------------------------------------------------------------------
# HTML/SVG 인라인
# ---------------------------------------------------------------------------


def render_org_chart_html(
    structure: dict[str, Any],
    *,
    title: str = "",
    tokens: IMDesignTokens | None = None,
) -> str:
    """조직도를 SVG 인라인으로 변환하여 HTML 반환."""
    try:
        dot = create_org_chart(structure, title=title, tokens=tokens)
        svg_str = _ce_graphviz_to_svg(dot)
        return f'<div class="org-chart-container">{svg_str}</div>'

    except Exception as e:
        logger.warning(f"조직도 SVG 생성 실패: {e}")
        # 폴백: 텍스트 기반 간이 표시
        nodes = structure.get("nodes", [])
        if not nodes:
            return '<div class="org-chart-container"><p>조직도 데이터 없음</p></div>'

        items = "".join(
            f"<li>{node.get('label', node.get('id', ''))}</li>" for node in nodes
        )
        return f'<div class="org-chart-container"><ul>{items}</ul></div>'
