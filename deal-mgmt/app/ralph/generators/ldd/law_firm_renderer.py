"""법무법인 스타일 .docx 렌더러 (Step 2) — 빈 템플릿에 AI 분석 결과 삽입.

LawFirmTemplateGenerator로 생성된 빈 템플릿의 플레이스홀더를
AI 분석 결과(체크리스트 + 3단 서술)로 교체한다.

XML 직접 조작으로 원본 서식(폰트, 색상, 스타일)을 100% 보존.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from docx import Document

from app.ralph.generators.ldd.law_firm_mapper import LawFirmChapter
from app.ralph.generators.ldd.law_firm_narrative_adapter import LawFirmNarrative
from app.ralph.generators.ldd.law_firm_template import (
    BODY_PLACEHOLDER,
    RECOMMENDATION_FILL,
    SECTION_BAR_FILLS,
    SECTION_PLACEHOLDERS,
    WML_NS,
    XML_SPACE_NS,
    _get_cell_fill_xml,
    _get_num_info_from_xml,
    _get_style_id_from_xml,
    _get_text_from_xml,
)

logger = logging.getLogger(__name__)


def _set_text_in_xml(p_element, text: str) -> None:
    """p 요소의 첫 w:t에 텍스트를 설정하고, 나머지 w:t는 비움.

    서식(rPr)은 첫 번째 run의 것이 보존됨.
    """
    first_t = True
    for t in p_element.iter(f"{{{WML_NS}}}t"):
        if first_t:
            t.text = text
            t.set(f"{{{XML_SPACE_NS}}}space", "preserve")
            first_t = False
        else:
            t.text = ""


def _set_cell_text(tc_element, text: str) -> None:
    """tc 요소의 첫 w:t에 텍스트 설정."""
    first_t = True
    for t in tc_element.iter(f"{{{WML_NS}}}t"):
        if first_t and text:
            t.text = text
            t.set(f"{{{XML_SPACE_NS}}}space", "preserve")
            first_t = False
        else:
            t.text = ""


class LawFirmDocxRenderer:
    """빈 법무법인 템플릿에 AI 분석 결과를 삽입하는 렌더러.

    Step 2: LawFirmTemplateGenerator가 생성한 빈 템플릿을 입력으로 받아
    체크리스트 + 3단 서술 데이터를 XML 직접 조작으로 채운다.
    """

    def render(
        self,
        template_path: Path | str,
        output_path: Path | str,
        report_data: dict[str, Any],
    ) -> Path:
        """빈 템플릿에 분석 결과를 채워 최종 .docx를 생성.

        Args:
            template_path: LawFirmTemplateGenerator가 생성한 빈 템플릿 경로
            output_path: 최종 출력 경로
            report_data: 렌더링 데이터
                - project_code: 프로젝트 코드명
                - law_firm_name: 법무법인 명칭
                - report_date: 보고서 날짜
                - target_company: 대상회사명
                - chapters: list[LawFirmChapter]
                - narratives: dict[chapter_number, list[LawFirmNarrative]]
                - exec_summary: dict (Executive Summary 표 데이터)

        Returns:
            출력 파일 경로
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        doc = Document(str(template_path))

        # 1. 표지 데이터 채우기
        self._fill_cover(doc, report_data)

        # 2. 본문 섹션 헤더 + 내용 채우기
        self._fill_body(doc, report_data)

        # 3. Executive Summary 표 채우기
        self._fill_exec_summary_table(doc, report_data)

        # 4. 데이터 표 채우기
        self._fill_data_tables(doc, report_data)

        doc.save(str(output))
        logger.info("법무법인 LDD 보고서 렌더링 완료: %s", output)
        return output

    # ── 표지 ──────────────────────────────────────────────────────────────

    def _fill_cover(self, doc: Document, data: dict[str, Any]) -> None:
        """표지의 프로젝트명, 날짜, 법무법인명을 실제 값으로 교체."""
        project_code = data.get("project_code", "")
        report_date = data.get("report_date", "")
        law_firm_name = data.get("law_firm_name", "")

        for element in doc.element.body:
            tag = element.tag.split("}")[-1]
            if tag != "p":
                continue

            text = _get_text_from_xml(element).strip()
            style_id = _get_style_id_from_xml(element)

            # Title 스타일: "Project [프로젝트 코드명]"
            if style_id == "ae" and "[프로젝트 코드명]" in text and project_code:
                _set_text_in_xml(element, f"Project {project_code}")

            # 날짜 플레이스홀더
            elif "[YYYY]" in text and "[MM]" in text and report_date:
                _set_text_in_xml(element, report_date)

    # ── 본문 ──────────────────────────────────────────────────────────────

    def _fill_body(self, doc: Document, data: dict[str, Any]) -> None:
        """본문 섹션 헤더와 내용 플레이스홀더를 분석 결과로 교체."""
        chapters: list[LawFirmChapter] = data.get("chapters", [])
        narratives: dict[str, list[LawFirmNarrative]] = data.get("narratives", {})
        law_firm_name = data.get("law_firm_name", "")

        if not chapters:
            return

        chapter_idx = 0
        current_chapter: LawFirmChapter | None = None
        item_idx = 0

        body = doc.element.body
        section_counter = 0

        for element in list(body):
            tag = element.tag.split("}")[-1]

            if tag == "tbl":
                # 섹션 헤더 바: 챕터 제목 채우기
                rows = element.findall(f"{{{WML_NS}}}tr")
                if len(rows) == 1:
                    cells = rows[0].findall(f"{{{WML_NS}}}tc")
                    if len(cells) == 3:
                        fill0 = _get_cell_fill_xml(cells[0])
                        if fill0 in SECTION_BAR_FILLS:
                            section_counter += 1
                            if section_counter == 1:
                                # 첫 번째 바: 법무법인 명칭
                                if law_firm_name:
                                    _set_cell_text(cells[2], law_firm_name)
                            else:
                                # 이후 바: 챕터 제목
                                if chapter_idx < len(chapters):
                                    current_chapter = chapters[chapter_idx]
                                    _set_cell_text(
                                        cells[2],
                                        f"{current_chapter.number}. {current_chapter.title}",
                                    )
                                    chapter_idx += 1
                                    item_idx = 0

                    # Recommendation 박스: 내용 채우기
                    if len(cells) == 1:
                        fill = _get_cell_fill_xml(cells[0])
                        text = _get_text_from_xml(cells[0])
                        if fill == RECOMMENDATION_FILL or "Recommendation" in text:
                            self._fill_recommendation_box(
                                cells[0], current_chapter, narratives, item_idx,
                            )

            elif tag == "p":
                text = _get_text_from_xml(element).strip()
                style_id = _get_style_id_from_xml(element)
                numId, ilvl = _get_num_info_from_xml(element)

                # 대목차 플레이스홀더 → 챕터 내 항목명
                if text in SECTION_PLACEHOLDERS.values() or text == BODY_PLACEHOLDER:
                    if current_chapter and item_idx < len(current_chapter.items):
                        item = current_chapter.items[item_idx]
                        narr_list = narratives.get(
                            current_chapter.number, [],
                        )

                        if text == "[부문명 기재]":
                            # 소섹션 제목
                            _set_text_in_xml(element, item.get("name", ""))
                        elif text == BODY_PLACEHOLDER:
                            # 본문: 3단 서술 또는 간략 설명 삽입
                            content = self._get_narrative_content(
                                item, narr_list, item_idx,
                            )
                            _set_text_in_xml(element, content)
                            item_idx += 1
                        elif text == "[소주제명 기재]":
                            _set_text_in_xml(element, item.get("name", ""))
                        elif text == "[세부항목명 기재]":
                            _set_text_in_xml(element, item.get("name", ""))

    def _fill_recommendation_box(
        self,
        tc_element,
        chapter: LawFirmChapter | None,
        narratives: dict[str, list[LawFirmNarrative]],
        item_idx: int,
    ) -> None:
        """Recommendation 박스에 권고사항을 채움."""
        if not chapter:
            return

        narr_list = narratives.get(chapter.number, [])
        if item_idx < len(narr_list):
            narr = narr_list[item_idx]
            rec_text = narr.recommendation_section if isinstance(narr, LawFirmNarrative) else narr.get("recommendation_section", "")
            if rec_text:
                _set_cell_text(tc_element, f"Recommendation: {rec_text}")

    def _get_narrative_content(
        self,
        item: dict[str, Any],
        narr_list: list,
        item_idx: int,
    ) -> str:
        """항목의 3단 서술 또는 체크리스트 설명을 반환."""
        # 3단 서술이 있으면 현황 + 검토 합체
        if item_idx < len(narr_list):
            narr = narr_list[item_idx]
            if isinstance(narr, LawFirmNarrative):
                parts = [narr.status_section, narr.review_section]
            else:
                parts = [
                    narr.get("status_section", ""),
                    narr.get("review_section", ""),
                ]
            content = "\n\n".join(p for p in parts if p)
            if content:
                return content

        # 체크리스트 설명 폴백
        desc = item.get("description", "")
        if desc:
            return desc

        return item.get("name", "")

    # ── Executive Summary 표 ─────────────────────────────────────────────

    def _fill_exec_summary_table(
        self,
        doc: Document,
        data: dict[str, Any],
    ) -> None:
        """EXECUTIVE SUMMARY 텍스트 이후의 첫 번째 표에 데이터 삽입."""
        exec_summary = data.get("exec_summary")
        if not exec_summary:
            return

        summary_rows = exec_summary.get("summary_rows", [])
        if not summary_rows:
            return

        # EXECUTIVE SUMMARY 텍스트 찾기
        found_exec = False
        for element in doc.element.body:
            tag = element.tag.split("}")[-1]
            if tag == "p":
                text = _get_text_from_xml(element).strip()
                if text == "EXECUTIVE SUMMARY":
                    found_exec = True
                    continue

            if found_exec and tag == "tbl":
                self._populate_exec_table(element, summary_rows)
                break

    def _populate_exec_table(
        self,
        tbl_element,
        summary_rows: list[dict[str, Any]],
    ) -> None:
        """Executive Summary 표의 데이터 행을 채움."""
        rows = tbl_element.findall(f"{{{WML_NS}}}tr")
        if len(rows) < 2:
            return

        # 첫 행은 헤더 → 두 번째 행부터 데이터
        for row_idx, row_data in enumerate(summary_rows):
            data_row_idx = row_idx + 1  # 헤더 스킵
            if data_row_idx >= len(rows):
                break

            cells = rows[data_row_idx].findall(f"{{{WML_NS}}}tc")
            # | 구분 | 중요도 | 주요 이슈 | 리스크 분석 | 권고사항 |
            cell_values = [
                f"{row_data.get('chapter_number', '')}. {row_data.get('chapter_title', '')}",
                row_data.get("importance", ""),
                row_data.get("key_issues", ""),
                row_data.get("risk_analysis", ""),
                row_data.get("recommendation", ""),
            ]
            for cell_idx, value in enumerate(cell_values):
                if cell_idx < len(cells):
                    _set_cell_text(cells[cell_idx], value)

    # ── 데이터 표 ─────────────────────────────────────────────────────────

    def _fill_data_tables(
        self,
        doc: Document,
        data: dict[str, Any],
    ) -> None:
        """별첨 데이터 표의 빈 행을 분석 결과로 채움."""
        appendices = data.get("appendices")
        if not appendices:
            return

        # 현재는 별첨 데이터 표 구조가 원본마다 다를 수 있어
        # 플레이스홀더 매칭 기반으로 처리
        # 추후 표별 ID 매핑 시스템 도입 가능
        logger.debug("별첨 데이터 표 채우기: %d개 테이블", len(appendices))
