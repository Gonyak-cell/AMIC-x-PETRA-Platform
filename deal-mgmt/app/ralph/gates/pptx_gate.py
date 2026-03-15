"""PPTX Programmatic Gate — python-pptx 기반 메모랜덤 프로그래밍 검증.

> 마지막 수정: 2026-03-13 21:33:25
"""

from __future__ import annotations

import re
import time
from typing import Any

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate
from app.ralph.korean_finance_dict import parse_korean_number


class PPTXProgrammaticGate(QualityGate):
    """TM/DM/IM PPTX 프로그래밍 검증 게이트.

    5개 검증 레이어:
    1. 슬라이드 구조 검증 (필수 슬라이드, 순서)
    2. 텍스트 완전성 (플레이스홀더 부재)
    3. 재무 테이블 수치 정합성
    4. 차트 데이터 유효성
    5. 디자인 일관성 (폰트, 색상, 포지션)
    """

    # memo_generator.py에서 가져온 디자인 상수
    ALLOWED_FONTS = {"SUIT Medium", "SUIT", "Arial", "Calibri", "맑은 고딕"}
    COLOR_DARK_GREEN = "0F3A32"
    COLOR_LIGHT_GREEN = "26C260"
    COLOR_DARK_GRAY = "3D3D3D"
    ALLOWED_COLORS = {COLOR_DARK_GREEN, COLOR_LIGHT_GREEN, COLOR_DARK_GRAY, "000000", "FFFFFF", "666666", "999999"}

    REQUIRED_SLIDES = {
        "TM": ["Cover", "Disclaimer", "Table of Contents"],
        "DM": ["Cover", "Disclaimer"],
        "IM": ["Cover", "Disclaimer", "Table of Contents"],
    }

    _PLACEHOLDER_PATTERNS = [
        r"\[INSERT\s*(?:HERE)?\]",
        r"\[TBD\]",
        r"\[XXX\]",
        r"\[TODO\]",
        r"\[금액\]",
        r"\[프로젝트명\]",
        r"Lorem\s+ipsum",
    ]

    @property
    def name(self) -> str:
        return "pptx_programmatic"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        start = time.perf_counter_ns()
        issues: list[str] = []
        suggestions: list[str] = []
        critical_flags: list[str] = []

        try:
            from pptx import Presentation

            prs = Presentation(artifact_path)
        except Exception as exc:
            return self._timed_result(
                start,
                [],
                [f"PPTX 로드 실패: {exc}"],
                [],
                [f"PPTX 파일 손상: {exc}"],
            )

        memo_type = prd_section.get("memo_type", "IM")

        # 1. 슬라이드 구조 검증
        struct_score, struct_issues = self._check_structure(prs, memo_type, prd_section)
        issues.extend(struct_issues)

        # 2. 텍스트 완전성
        complete_score, complete_issues = self._check_completeness(prs)
        issues.extend(complete_issues)
        if any("CRITICAL" in i for i in complete_issues):
            critical_flags.extend([i for i in complete_issues if "CRITICAL" in i])

        # 3. 재무 테이블 정합성
        table_score, table_issues = self._check_table_totals(prs, source_data)
        issues.extend(table_issues)

        # 4. 차트 데이터 유효성
        chart_score, chart_issues = self._check_charts(prs)
        issues.extend(chart_issues)

        # 5. 디자인 일관성
        design_score, design_issues = self._check_design(prs)
        issues.extend(design_issues)

        dimensions = [
            DimensionScore("structure", "슬라이드 구조", struct_score, 0.20),
            DimensionScore("completeness", "텍스트 완전성", complete_score, 0.20),
            DimensionScore("table_integrity", "테이블 정합성", table_score, 0.25),
            DimensionScore("chart_validity", "차트 유효성", chart_score, 0.15),
            DimensionScore("design", "디자인 일관성", design_score, 0.20),
        ]

        # 6. 슬롯 적합성 (TemplateSpec 제공 시에만)
        template_spec = None
        if source_data and "template_spec" in source_data:
            template_spec = source_data["template_spec"]

        if template_spec is not None:
            slot_score, slot_issues, slot_crits = self._check_slot_compliance(prs, template_spec)
            issues.extend(slot_issues)
            critical_flags.extend(slot_crits)

            # 기존 5개 차원을 0.85배로 스케일링, 새 차원에 0.15 할당
            scaled: list[DimensionScore] = [
                DimensionScore(d.name, d.label, d.score, d.weight * 0.85, d.feedback) for d in dimensions
            ]
            scaled.append(DimensionScore("slot_compliance", "슬롯 적합성", slot_score, 0.15))
            dimensions = scaled

        return self._timed_result(
            start,
            dimensions,
            issues,
            suggestions,
            critical_flags,
        )

    # ── 검증 레이어 ──────────────────────────────────────────────────────────

    def _check_structure(self, prs: Any, memo_type: str, prd: dict) -> tuple[float, list[str]]:
        """슬라이드 구조 검증."""
        issues: list[str] = []
        slide_count = len(prs.slides)

        # 최소 슬라이드 수
        min_slides = prd.get("min_slides", 5)
        if slide_count < min_slides:
            issues.append(f"슬라이드 수 부족: {slide_count}장 (최소 {min_slides}장)")

        # 필수 슬라이드 존재 확인
        slide_titles = []
        for slide in prs.slides:
            if slide.shapes.title:
                slide_titles.append(slide.shapes.title.text.strip())
            else:
                # title placeholder가 없는 경우 첫 텍스트 프레임 사용
                for shape in slide.shapes:
                    if shape.has_text_frame and shape.text_frame.text.strip():
                        slide_titles.append(shape.text_frame.text.strip())
                        break
                else:
                    slide_titles.append("")

        required = self.REQUIRED_SLIDES.get(memo_type, [])
        for req in required:
            if not any(req.lower() in t.lower() for t in slide_titles):
                issues.append(f"필수 슬라이드 누락: '{req}'")

        score = max(1.0, 5.0 - len(issues) * 1.0)
        return score, issues

    def _check_completeness(self, prs: Any) -> tuple[float, list[str]]:
        """플레이스홀더 패턴 탐지."""
        issues: list[str] = []
        placeholder_count = 0

        for slide_idx, slide in enumerate(prs.slides, 1):
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                text = shape.text_frame.text
                for pattern in self._PLACEHOLDER_PATTERNS:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        placeholder_count += len(matches)
                        issues.append(f"CRITICAL: 슬라이드 {slide_idx} — 플레이스홀더 '{matches[0]}'")

        score = 5.0 if placeholder_count == 0 else max(1.0, 5.0 - placeholder_count)
        return score, issues

    def _check_table_totals(self, prs: Any, source_data: dict | None) -> tuple[float, list[str]]:
        """재무 테이블 합계행 정합성."""
        issues: list[str] = []
        table_count = 0
        error_count = 0

        for slide_idx, slide in enumerate(prs.slides, 1):
            for shape in slide.shapes:
                if not shape.has_table:
                    continue
                table = shape.table
                table_count += 1

                rows = len(table.rows)
                cols = len(table.columns)
                if rows < 3 or cols < 2:
                    continue  # 너무 작은 테이블은 합계 검증 불필요

                # 마지막 행을 합계행으로 간주
                last_row_text = [table.cell(rows - 1, c).text.strip() for c in range(cols)]
                # "합계", "Total", "소계" 패턴 확인
                if not any(kw in last_row_text[0].lower() for kw in ["합계", "total", "소계", "계"]):
                    continue

                # 데이터 열에 대해 합계 검증
                for c in range(1, cols):
                    total_val = parse_korean_number(table.cell(rows - 1, c).text)
                    if total_val is None:
                        continue

                    item_sum = 0.0
                    parseable = True
                    for r in range(1, rows - 1):
                        val = parse_korean_number(table.cell(r, c).text)
                        if val is None:
                            parseable = False
                            break
                        item_sum += val

                    if parseable and abs(total_val - item_sum) > 0.01:
                        error_count += 1
                        issues.append(
                            f"슬라이드 {slide_idx} 테이블: 열 {c + 1} 합계={total_val}, "
                            f"항목합={item_sum} (차이: {abs(total_val - item_sum):.2f})"
                        )

        if table_count == 0:
            return 5.0, []

        score = max(1.0, 5.0 - error_count * 2.0)
        return score, issues

    def _check_charts(self, prs: Any) -> tuple[float, list[str]]:
        """차트 데이터 유효성."""
        issues: list[str] = []
        chart_count = 0

        for slide_idx, slide in enumerate(prs.slides, 1):
            for shape in slide.shapes:
                if not shape.has_chart:
                    continue
                chart = shape.chart
                chart_count += 1

                # 데이터 존재 확인
                for plot in chart.plots:
                    for series in plot.series:
                        values = list(series.values)
                        if not values or all(v is None for v in values):
                            issues.append(f"슬라이드 {slide_idx}: 차트 시리즈에 데이터 없음")

                # 차트 제목 확인
                if not chart.has_title:
                    issues.append(f"슬라이드 {slide_idx}: 차트 제목 없음")

        if chart_count == 0:
            return 5.0, []

        score = max(1.0, 5.0 - len(issues) * 1.0)
        return score, issues

    def _check_design(self, prs: Any) -> tuple[float, list[str]]:
        """디자인 일관성 검증."""
        issues: list[str] = []
        font_violations = 0
        color_violations = 0

        for slide_idx, slide in enumerate(prs.slides, 1):
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        # 폰트 확인 (None = 테마 상속, 허용)
                        if run.font.name and run.font.name not in self.ALLOWED_FONTS:
                            font_violations += 1
                            if font_violations <= 3:
                                issues.append(f"슬라이드 {slide_idx}: 비허용 폰트 '{run.font.name}'")

                        # 색상 확인 (테마 색상 _SchemeColor는 .rgb 없음)
                        try:
                            color_rgb = run.font.color.rgb if run.font.color else None
                        except (AttributeError, TypeError):
                            color_rgb = None
                        if color_rgb is not None:
                            rgb = str(color_rgb)
                            if rgb not in self.ALLOWED_COLORS:
                                color_violations += 1
                                if color_violations <= 3:
                                    issues.append(f"슬라이드 {slide_idx}: 비허용 색상 #{rgb}")

        total_violations = font_violations + color_violations
        score = max(1.0, 5.0 - total_violations * 0.3)
        return score, issues

    # ── SlotSpec 기반 검증 ──────────────────────────────────────────────────

    def _check_slot_compliance(
        self,
        prs: Any,
        template_spec: Any,
    ) -> tuple[float, list[str], list[str]]:
        """SlotSpec 기반 콘텐츠 적합성 검증.

        TemplateSpec이 제공된 경우에만 호출된다.
        텍스트 overflow, 폰트 크기 위반, 빈 슬라이드, 슬롯 수를 검증한다.

        Returns:
            (score, issues, critical_flags) 튜플
        """
        from pptx.util import Pt

        issues: list[str] = []
        critical_flags: list[str] = []

        slides = list(prs.slides)
        spec_slides = list(template_spec.slides) if template_spec.slides else []

        for slide_idx, slide in enumerate(slides, 1):
            # 빈 슬라이드 감지 — shape가 0개이거나 placeholder만 있는 경우
            real_shapes = [s for s in slide.shapes if not s.is_placeholder]
            if len(slide.shapes) == 0 or len(real_shapes) == 0:
                issues.append(f"슬라이드 {slide_idx}: 빈 슬라이드 (실질 shape 없음)")

            # SlideSpec 매칭 (인덱스 기반 — spec 범위 내에서만)
            if slide_idx - 1 >= len(spec_slides):
                continue
            slide_spec = spec_slides[slide_idx - 1]

            # 슬롯 수 검증: 실제 shape 수가 required_shapes보다 적으면
            if slide_spec.required_shapes:
                shape_names = {s.name for s in slide.shapes if s.name}
                missing = [rn for rn in slide_spec.required_shapes if rn not in shape_names]
                if missing:
                    issues.append(f"슬라이드 {slide_idx}: 필수 shape 누락 — {missing}")

            # 각 SlotSpec에 대한 검증
            for slot in slide_spec.slots:
                # TEXT 슬롯 검증
                if slot.content_type == "TEXT":
                    self._check_text_slot(slide, slide_idx, slot, issues, critical_flags)

                # 모든 슬롯 유형에 대해 min_font_pt 검증
                if slot.min_font_pt is not None:
                    self._check_font_size(slide, slide_idx, slot, Pt, issues)

        # 점수 계산: 위반 1건당 -0.5, 최소 1.0
        total_violations = len(issues) + len(critical_flags)
        score = max(1.0, 5.0 - total_violations * 0.5)
        return score, issues, critical_flags

    def _check_text_slot(
        self,
        slide: Any,
        slide_idx: int,
        slot: Any,
        issues: list[str],
        critical_flags: list[str],
    ) -> None:
        """TEXT 슬롯의 max_chars/max_lines overflow를 검증한다."""
        # slot.name으로 shape 매칭
        target_shape = None
        for shape in slide.shapes:
            if shape.name == slot.name:
                target_shape = shape
                break

        if target_shape is None or not target_shape.has_text_frame:
            return

        text = target_shape.text_frame.text
        is_fail_policy = str(getattr(slot, "overflow_policy", "FAIL")) == "FAIL"

        # max_chars 초과 검증
        if slot.max_chars is not None and len(text) > slot.max_chars:
            msg = f"슬라이드 {slide_idx} '{slot.name}': 글자 수 초과 ({len(text)}/{slot.max_chars})"
            if is_fail_policy:
                critical_flags.append(f"CRITICAL: {msg}")
            else:
                issues.append(msg)

        # max_lines 초과 검증
        if slot.max_lines is not None:
            line_count = len(target_shape.text_frame.paragraphs)
            if line_count > slot.max_lines:
                msg = f"슬라이드 {slide_idx} '{slot.name}': 줄 수 초과 ({line_count}/{slot.max_lines})"
                if is_fail_policy:
                    critical_flags.append(f"CRITICAL: {msg}")
                else:
                    issues.append(msg)

    def _check_font_size(
        self,
        slide: Any,
        slide_idx: int,
        slot: Any,
        pt_class: type,
        issues: list[str],
    ) -> None:
        """슬롯 내 run의 폰트 크기가 min_font_pt 이상인지 검증한다."""
        target_shape = None
        for shape in slide.shapes:
            if shape.name == slot.name:
                target_shape = shape
                break

        if target_shape is None or not target_shape.has_text_frame:
            return

        min_emu = pt_class(slot.min_font_pt)
        for para in target_shape.text_frame.paragraphs:
            for run in para.runs:
                if run.font.size is not None and run.font.size < min_emu:
                    actual_pt = run.font.size / pt_class(1)
                    issues.append(
                        f"슬라이드 {slide_idx} '{slot.name}': 폰트 크기 미달 ({actual_pt:.1f}pt < {slot.min_font_pt}pt)"
                    )
                    return  # 슬롯당 1건만 보고
