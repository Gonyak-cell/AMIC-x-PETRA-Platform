"""DOCX 파서 — 한국어 계약서 DOCX에서 조항 구조를 추출한다.

"제N조", "제N조의N" 패턴을 인식하여 조항 제목/본문을 분리한다.
python-docx를 사용하며, 실패 시 빈 리스트를 반환한다.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from .base import ClauseData

logger = logging.getLogger(__name__)

# 한국어 조항 번호 패턴: "제1조", "제12조", "제3조의2"
_CLAUSE_TITLE_RE = re.compile(r"^제\s*(\d+)\s*조(?:의\s*(\d+))?\s*(?:\(([^)]+)\))?\s*$")

# Heading 스타일 패턴 (python-docx 스타일명)
_HEADING_STYLES = {"Heading 1", "Heading 2", "Heading1", "Heading2", "제목 1", "제목 2"}


def parse_docx(path: str | Path) -> list[ClauseData]:
    """DOCX 파일에서 조항 구조를 추출한다.

    Args:
        path: DOCX 파일 경로

    Returns:
        추출된 조항 리스트 (clause_order는 1부터 시작)
    """
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx 미설치 — pip install python-docx")
        return []

    filepath = Path(path)
    if not filepath.exists():
        logger.warning("파일 미존재: %s", filepath)
        return []

    if filepath.suffix.lower() not in (".docx",):
        logger.warning("지원하지 않는 형식: %s (DOCX만 지원)", filepath.suffix)
        return []

    try:
        doc = Document(str(filepath))
    except Exception:
        logger.exception("DOCX 파싱 실패: %s", filepath)
        return []

    return _extract_clauses(doc)


def _extract_clauses(doc: Any) -> list[ClauseData]:
    """Document 객체에서 조항을 추출한다.

    Args:
        doc: python-docx Document 인스턴스 (런타임 동적 import).
    """
    clauses: list[ClauseData] = []
    current_title: str | None = None
    current_content_parts: list[str] = []
    clause_order = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = para.style.name if para.style else ""
        is_heading = style_name in _HEADING_STYLES

        # 조항 제목 감지: Heading 스타일 또는 "제N조" 패턴
        title_match = _CLAUSE_TITLE_RE.match(text)
        is_clause_start = is_heading and title_match is not None

        # Heading이 아니더라도 "제N조 (제목)" 패턴이면 조항 시작으로 처리
        if not is_clause_start and title_match is not None:
            # "제N조 (제목)" 형식 전체 라인
            if "(" in text:
                is_clause_start = True

        if is_clause_start and title_match:
            # 이전 조항 저장
            if current_title is not None:
                clause_order += 1
                clauses.append(
                    ClauseData(
                        clause_order=clause_order,
                        title=current_title,
                        content=_build_html_content(current_content_parts),
                    )
                )
                current_content_parts = []

            # 새 조항 시작
            title_in_parens = title_match.group(3)
            if title_in_parens:
                current_title = title_in_parens
            else:
                current_title = text
        elif current_title is not None:
            # 조항 본문 축적
            current_content_parts.append(_paragraph_to_html(para))

    # 마지막 조항 저장
    if current_title is not None:
        clause_order += 1
        clauses.append(
            ClauseData(
                clause_order=clause_order,
                title=current_title,
                content=_build_html_content(current_content_parts),
            )
        )

    return clauses


def _paragraph_to_html(para: Any) -> str:
    """python-docx Paragraph를 간단한 HTML로 변환한다.

    Args:
        para: python-docx Paragraph 인스턴스 (런타임 동적 import).
    """
    text = para.text.strip()
    if not text:
        return ""

    style_name = para.style.name if para.style else ""

    # 번호 목록 항목 감지
    if style_name.startswith("List") or text.startswith(("①", "②", "③", "④", "⑤", "1.", "2.", "3.")):
        return f"<li>{text}</li>"

    # Heading 2 → 소제목
    if style_name in ("Heading 2", "Heading2", "제목 2"):
        return f"<h3>{text}</h3>"

    # 일반 본문
    return f"<p>{text}</p>"


def _build_html_content(parts: list[str]) -> str:
    """HTML 파트를 하나의 콘텐츠 블록으로 합친다."""
    filtered = [p for p in parts if p]
    if not filtered:
        return "<p></p>"

    # 연속 <li> 항목을 <ol>로 감싸기
    result: list[str] = []
    in_list = False

    for part in filtered:
        if part.startswith("<li>"):
            if not in_list:
                result.append("<ol>")
                in_list = True
            result.append(part)
        else:
            if in_list:
                result.append("</ol>")
                in_list = False
            result.append(part)

    if in_list:
        result.append("</ol>")

    return "\n".join(result)
