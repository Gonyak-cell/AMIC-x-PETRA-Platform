"""Excalidraw PNG 다이어그램 리졸버 — PPTX 파이프라인 통합.

Excalidraw에서 사용자가 편집·내보내기한 PNG가 존재하면 Graphviz 자동
생성 대신 해당 PNG를 PPTX 슬라이드에 삽입한다.

PNG 저장 경로 규칙:
    {output_dir}/diagrams/{document_id}/{diagram_type}_{diagram_id}.png
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def find_excalidraw_png(
    output_dir: str,
    document_id: str,
    diagram_type: str,
) -> Path | None:
    """주어진 문서·다이어그램 유형에 대한 Excalidraw PNG를 검색한다.

    Args:
        output_dir: IM 출력 루트 디렉토리 (예: ``output/``).
        document_id: 문서 UUID 문자열.
        diagram_type: 다이어그램 유형
            (``shareholding``, ``org_chart``, ``deal_structure``,
             ``value_chain``, ``custom``).

    Returns:
        PNG 파일 경로. 없으면 ``None``.
    """
    diagram_dir = Path(output_dir) / "diagrams" / document_id
    if not diagram_dir.is_dir():
        return None

    # {diagram_type}_{uuid}.png 패턴 매칭
    matches = sorted(
        diagram_dir.glob(f"{diagram_type}_*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if matches:
        logger.info(
            "Excalidraw PNG 발견: %s (총 %d개 중 최신)",
            matches[0].name,
            len(matches),
        )
        return matches[0]
    return None


def insert_diagram_pptx(
    slide: Any,
    png_path: Path,
    *,
    left: float = 0.5,
    top: float = 1.5,
    width: float = 9.0,
    height: float = 4.5,
) -> bool:
    """PNG 파일을 PPTX 슬라이드에 삽입한다.

    Args:
        slide: python-pptx 슬라이드 객체.
        png_path: 삽입할 PNG 파일 경로.
        left: 좌측 여백 (인치).
        top: 상단 여백 (인치).
        width: 이미지 너비 (인치).
        height: 이미지 높이 (인치).

    Returns:
        삽입 성공 여부.
    """
    from pptx.util import Inches

    if not png_path.exists():
        logger.warning("PNG 파일 없음: %s", png_path)
        return False

    slide.shapes.add_picture(
        str(png_path),
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    logger.info("다이어그램 PNG 삽입 완료: %s", png_path.name)
    return True


def render_diagram_pptx_with_fallback(
    slide: Any,
    output_dir: str,
    document_id: str,
    diagram_type: str,
    *,
    graphviz_fallback: Any | None = None,
    left: float = 0.5,
    top: float = 1.5,
    width: float = 9.0,
    height: float = 4.5,
) -> bool:
    """Excalidraw PNG 우선 → Graphviz 폴백으로 다이어그램을 삽입한다.

    Args:
        slide: python-pptx 슬라이드 객체.
        output_dir: IM 출력 루트 디렉토리.
        document_id: 문서 UUID 문자열.
        diagram_type: 다이어그램 유형.
        graphviz_fallback: Excalidraw PNG 없을 때 호출할 콜백.
            ``Callable[[slide], None]`` 형태.
        left: 좌측 여백 (인치).
        top: 상단 여백 (인치).
        width: 이미지 너비 (인치).
        height: 이미지 높이 (인치).

    Returns:
        다이어그램 삽입 성공 여부.
    """
    png = find_excalidraw_png(output_dir, document_id, diagram_type)
    if png:
        return insert_diagram_pptx(
            slide, png, left=left, top=top, width=width, height=height
        )

    if graphviz_fallback is not None:
        logger.info(
            "Excalidraw PNG 없음 → Graphviz 폴백 실행 (type=%s)",
            diagram_type,
        )
        graphviz_fallback(slide)
        return True

    logger.warning(
        "다이어그램 렌더링 불가: Excalidraw PNG 없고 Graphviz 폴백 미제공 (type=%s)",
        diagram_type,
    )
    return False
