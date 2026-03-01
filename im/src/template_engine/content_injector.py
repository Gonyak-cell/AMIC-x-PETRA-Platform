"""콘텐츠 인젝터 — 마스터 PPTX 템플릿의 shape에 데이터를 삽입한다.

핵심 원칙: **서식 유지**. 텍스트/차트/테이블의 데이터만 교체하고,
폰트, 크기, 색상, 축, 레이블 등 시각적 서식은 원본 템플릿 그대로 보존한다.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from pptx.chart.data import CategoryChartData
from pptx.oxml.ns import qn

from src.template_engine.schemas import ChartContent, TableContent

if TYPE_CHECKING:
    from pptx.chart.chart import Chart
    from pptx.shapes.autoshape import Shape
    from pptx.shapes.graphfrm import GraphicFrame
    from pptx.table import Table

logger = logging.getLogger(__name__)


class ContentInjector:
    """마스터 PPTX 템플릿의 shape에 데이터를 삽입하는 엔진."""

    # ── 텍스트 삽입 ──────────────────────────────────────────────────────

    @staticmethod
    def inject_text(shape: Shape, content: str, *, preserve_format: bool = True) -> None:
        """텍스트 shape의 내용만 교체한다.

        preserve_format=True일 때:
        - 첫 번째 paragraph의 첫 번째 run 서식(폰트, 크기, 색상, 볼드)을 복제
        - 내용만 새 텍스트로 교체
        - 나머지 paragraph/run은 제거

        preserve_format=False일 때:
        - text_frame.text를 직접 교체 (서식 손실 가능)

        멀티라인 분리 규칙 (preserve_format=True):
        - 줄바꿈(\\n)이 포함된 경우: \\n 기준으로 분리 (파이프는 일반 텍스트로 취급)
        - 줄바꿈이 없는 경우: 파이프(|) 기준으로 분리
        - 즉, 줄바꿈이 우선. 두 구분자가 혼용되면 파이프는 무시됨.
        """
        if not shape.has_text_frame:
            logger.warning("shape %r 에 text_frame 없음 — 스킵", shape.name)
            return

        tf = shape.text_frame

        if not preserve_format or not tf.paragraphs:
            tf.text = content
            return

        # 멀티라인 분리 (파이프 또는 줄바꿈)
        lines = content.split("\n") if "\n" in content else content.split("|")

        # 원본 첫 paragraph → 서식 복제 기준
        ref_para = tf.paragraphs[0]
        ref_run = ref_para.runs[0] if ref_para.runs else None

        # 기존 paragraph 모두 제거 (XML 직접 조작)
        p_elements = list(tf._txBody)
        for p_elem in p_elements:
            if p_elem.tag.endswith("}p"):
                tf._txBody.remove(p_elem)

        # 새 paragraph 생성 (서식 복제 + 텍스트 교체)
        for line in lines:
            new_p = copy.deepcopy(ref_para._p)
            tf._txBody.append(new_p)
            # run 텍스트만 교체
            for r_elem in new_p.findall(qn("a:r")):
                t_elem = r_elem.find(qn("a:t"))
                if t_elem is not None:
                    t_elem.text = line
                    break
            else:
                # run이 없으면 새로 생성
                _append_run_to_p(new_p, line, ref_run)

    # ── 차트 데이터 삽입 ──────────────────────────────────────────────────

    @staticmethod
    def inject_chart_data(shape: GraphicFrame, content: ChartContent) -> None:
        """네이티브 PPTX 차트의 데이터만 교체한다.

        chart.replace_data()를 사용하여 카테고리와 시리즈 데이터만 변경.
        색상, 축, 레이블, 제목 등 디자인 서식은 자동 보존된다.
        """
        if not shape.has_chart:
            logger.warning("shape %r 에 차트 없음 — 스킵", shape.name)
            return

        chart: Chart = shape.chart

        chart_data = CategoryChartData()
        chart_data.categories = content.categories

        for series in content.series:
            chart_data.add_series(series.name, series.values)

        chart.replace_data(chart_data)
        logger.debug(
            "차트 데이터 교체: %s — %d 카테고리, %d 시리즈",
            shape.name,
            len(content.categories),
            len(content.series),
        )

    # ── 테이블 데이터 삽입 ────────────────────────────────────────────────

    @staticmethod
    def inject_table_data(
        shape: GraphicFrame,
        content: TableContent,
        *,
        preserve_header: bool = True,
    ) -> None:
        """테이블 셀의 데이터만 교체한다.

        preserve_header=True일 때 첫 번째 행(헤더)은 변경하지 않고,
        데이터 행만 교체한다. 셀의 서식(테두리, 배경색, 폰트)은 보존된다.

        데이터 행 수가 기존 테이블보다 적으면 남은 행은 빈 문자열로 채운다.
        데이터 행 수가 기존 테이블보다 많으면 테이블 범위 내에서만 채운다.
        """
        if not shape.has_table:
            logger.warning("shape %r 에 테이블 없음 — 스킵", shape.name)
            return

        table: Table = shape.table
        num_cols = len(table.columns)
        num_rows = len(table.rows)

        # 헤더 교체 (옵션)
        start_row = 0
        if content.headers and not preserve_header:
            for ci, header in enumerate(content.headers[:num_cols]):
                _set_cell_text(table.cell(0, ci), header)
            start_row = 1
        elif preserve_header:
            start_row = 1

        # 데이터 행 교체
        for ri, row_data in enumerate(content.rows):
            table_row_idx = start_row + ri
            if table_row_idx >= num_rows:
                logger.debug(
                    "테이블 %s: 데이터 행 %d개 중 %d개만 삽입 (테이블 크기 초과)",
                    shape.name, len(content.rows), ri,
                )
                break

            for ci, cell_value in enumerate(row_data[:num_cols]):
                _set_cell_text(table.cell(table_row_idx, ci), cell_value)

        # 남은 행 비우기
        for ri in range(start_row + len(content.rows), num_rows):
            for ci in range(num_cols):
                _set_cell_text(table.cell(ri, ci), "")

        logger.debug(
            "테이블 데이터 교체: %s — %d행 × %d열",
            shape.name,
            min(len(content.rows), num_rows - start_row),
            num_cols,
        )

    # ── AutoShape 텍스트 삽입 ─────────────────────────────────────────────

    @staticmethod
    def inject_auto_shape_text(shape: Shape, content: str) -> None:
        """AutoShape(섹션 헤더, 콘텐츠 박스)의 텍스트만 교체한다.

        inject_text와 동일하지만, AutoShape 전용 명칭을 제공한다.
        """
        ContentInjector.inject_text(shape, content, preserve_format=True)


# ── 헬퍼 함수 ───────────────────────────────────────────────────────────────


def _set_cell_text(cell: object, text: str) -> None:
    """테이블 셀의 텍스트만 교체한다 (서식 보존).

    첫 번째 paragraph의 첫 번째 run 텍스트만 변경한다.
    run이 없으면 새로 추가한다.
    """
    tf = cell.text_frame  # type: ignore[attr-defined]
    if tf.paragraphs and tf.paragraphs[0].runs:
        tf.paragraphs[0].runs[0].text = text
        # 두 번째 이후 run 제거 (기존 텍스트가 여러 run으로 분리된 경우)
        p = tf.paragraphs[0]._p
        runs = p.findall(qn("a:r"))
        for extra_run in runs[1:]:
            p.remove(extra_run)
    else:
        tf.text = text


def _append_run_to_p(
    p_element: object,
    text: str,
    ref_run: object | None,
) -> None:
    """paragraph XML 요소에 run을 추가한다."""
    from lxml import etree

    r = etree.SubElement(p_element, qn("a:r"))  # type: ignore[arg-type]

    # 서식 복제
    if ref_run is not None:
        rPr_source = ref_run._r.find(qn("a:rPr"))  # type: ignore[attr-defined]
        if rPr_source is not None:
            r.insert(0, copy.deepcopy(rPr_source))

    t = etree.SubElement(r, qn("a:t"))
    t.text = text
