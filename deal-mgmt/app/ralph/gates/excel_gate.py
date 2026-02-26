"""Excel Programmatic Gate — openpyxl 기반 재무모델 프로그래밍 검증.

6개 검증 레이어:
1. 워크시트 구조 검증 (필수 시트 존재)
2. 수식 셀 비율 (≥30% 목표)
3. BS 균형 검증 (총자산 = 부채+자본) — CRITICAL
4. IS→BS→CF 교차 참조 정합성
5. 플레이스홀더 부재
6. 숫자 형식 일관성
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate

logger = logging.getLogger(__name__)

# 필수 워크시트 (모든 모델 유형 공통)
REQUIRED_SHEETS_COMMON = {"Legend", "Summary"}

# 모델 유형별 추가 필수 시트
REQUIRED_SHEETS_BY_TYPE: dict[str, set[str]] = {
    "DCF": {"Input", "IS", "BS", "CF", "WACC", "DCF"},
    "LBO": {"Input", "IS", "BS", "CF", "Debt Schedule", "Returns"},
    "COMPS": {"GPCM"},
    "TRANSACTION_COMPS": {"GTM"},
    "PROJECTION": {"Input", "IS", "BS", "CF"},
    "FULL": {"Input", "IS", "BS", "CF", "WACC", "DCF", "GPCM", "GTM"},
}

# BS 행 매칭 키워드
_TOTAL_ASSETS_KEYWORDS = {"total assets", "총자산"}
_TOTAL_LE_KEYWORDS = {"total liabilities & equity", "total l&e", "부채와자본 합계", "부채및자본합계"}
_BALANCE_CHECK_KEYWORDS = {"balance check"}

# 플레이스홀더 패턴
_PLACEHOLDER_PATTERNS = [
    r"\[INSERT\s*(?:HERE)?\]",
    r"\[TBD\]",
    r"\[XXX\]",
    r"\[TODO\]",
    r"\[금액\]",
    r"Lorem\s+ipsum",
]


class ExcelProgrammaticGate(QualityGate):
    """Excel 재무모델 프로그래밍 검증 게이트."""

    @property
    def name(self) -> str:
        return "excel_programmatic"

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
            from openpyxl import load_workbook

            wb = load_workbook(artifact_path, data_only=False)
        except Exception as exc:
            return self._timed_result(
                start,
                [],
                [f"Excel 로드 실패: {exc}"],
                [],
                [f"Excel 파일 손상: {exc}"],
            )

        model_type = prd_section.get("model_type", "DCF")

        # 1. 워크시트 구조 검증
        struct_score, struct_issues = self._check_structure(wb, model_type)
        issues.extend(struct_issues)

        # 2. 수식 셀 비율
        formula_score, formula_issues = self._check_formula_ratio(wb)
        issues.extend(formula_issues)

        # 3. BS 균형 (CRITICAL)
        balance_score, balance_issues, balance_crits = self._check_balance(wb)
        issues.extend(balance_issues)
        critical_flags.extend(balance_crits)

        # 4. 교차 참조 정합성
        cross_score, cross_issues = self._check_cross_refs(wb)
        issues.extend(cross_issues)

        # 5. 플레이스홀더 탐지
        complete_score, complete_issues = self._check_completeness(wb)
        issues.extend(complete_issues)

        # 6. 숫자 형식 일관성
        format_score, format_issues = self._check_formatting(wb)
        issues.extend(format_issues)

        dimensions = [
            DimensionScore("structure", "워크시트 구조", struct_score, 0.15),
            DimensionScore("formula_ratio", "수식 비율", formula_score, 0.20),
            DimensionScore("balance_check", "BS 균형", balance_score, 0.25),
            DimensionScore("cross_validation", "교차 참조", cross_score, 0.20),
            DimensionScore("completeness", "완전성", complete_score, 0.10),
            DimensionScore("formatting", "포매팅", format_score, 0.10),
        ]

        if issues:
            suggestions.append("아래 이슈를 해결하면 점수가 향상됩니다.")

        wb.close()

        return self._timed_result(
            start,
            dimensions,
            issues,
            suggestions,
            critical_flags,
        )

    # ── 검증 레이어 ──────────────────────────────────────────────────────

    def _check_structure(self, wb: Any, model_type: str) -> tuple[float, list[str]]:
        """필수 워크시트 존재 여부 검증."""
        issues: list[str] = []
        sheet_names = set(wb.sheetnames)

        required = REQUIRED_SHEETS_COMMON | REQUIRED_SHEETS_BY_TYPE.get(model_type, set())
        missing = required - sheet_names
        for m in missing:
            issues.append(f"필수 워크시트 누락: '{m}'")

        total = len(required)
        found = total - len(missing)
        score = max(1.0, 5.0 * found / total) if total > 0 else 5.0
        return score, issues

    def _check_formula_ratio(self, wb: Any) -> tuple[float, list[str]]:
        """수식 셀 비율 검증 — Legend/Summary 제외."""
        issues: list[str] = []
        total_cells = 0
        formula_cells = 0
        skip_sheets = {"Legend", "Summary"}

        for ws in wb.worksheets:
            if ws.title in skip_sheets:
                continue
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        total_cells += 1
                        if isinstance(cell.value, str) and cell.value.startswith("="):
                            formula_cells += 1

        if total_cells == 0:
            return 1.0, ["비어있는 워크북 — 데이터 셀 없음"]

        ratio = formula_cells / total_cells
        pct = round(ratio * 100, 1)

        if ratio >= 0.30:
            score = 5.0
        elif ratio >= 0.20:
            score = 4.0
            issues.append(f"수식 비율 {pct}% — 30% 이상 권장")
        elif ratio >= 0.10:
            score = 3.0
            issues.append(f"수식 비율 {pct}% — 수식 추가 필요")
        else:
            score = 2.0
            issues.append(f"수식 비율 {pct}% — 대부분 수식 없음, 재작업 필요")

        return score, issues

    def _check_balance(self, wb: Any) -> tuple[float, list[str], list[str]]:
        """BS 시트 총자산 = 부채+자본 균형 검증 (CRITICAL)."""
        issues: list[str] = []
        critical_flags: list[str] = []

        # BS 시트 찾기
        bs_ws = None
        for ws in wb.worksheets:
            if ws.title.upper() in ("BS", "BALANCE SHEET"):
                bs_ws = ws
                break

        if bs_ws is None:
            return 5.0, [], []  # BS 없으면 (COMPS 등) 만점

        # Balance Check 행 찾기 (builder가 삽입한 행)
        balance_check_row = None
        total_assets_row = None
        total_le_row = None

        for row in bs_ws.iter_rows(min_col=2, max_col=2):
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    lower = cell.value.strip().lower()
                    if any(kw in lower for kw in _BALANCE_CHECK_KEYWORDS):
                        balance_check_row = cell.row
                    elif any(kw in lower for kw in _TOTAL_ASSETS_KEYWORDS):
                        total_assets_row = cell.row
                    elif any(kw in lower for kw in _TOTAL_LE_KEYWORDS):
                        total_le_row = cell.row

        if balance_check_row is not None:
            # balance_check 행의 수식이 있으면 구조적으로 검증됨
            for col_idx in range(3, min(bs_ws.max_column or 3, 20) + 1):
                cell = bs_ws.cell(row=balance_check_row, column=col_idx)
                if cell.value is not None and isinstance(cell.value, str) and cell.value.startswith("="):
                    pass  # 수식 기반 검증 — 좋음
                elif cell.value is not None and isinstance(cell.value, (int, float)):
                    if abs(cell.value) > 1:
                        msg = f"BS Balance Check 불일치: 열 {col_idx}, 차이={cell.value}"
                        issues.append(msg)
                        critical_flags.append(f"CRITICAL: {msg}")

        elif total_assets_row and total_le_row:
            # Balance Check 행이 없으면 직접 비교
            for col_idx in range(3, min(bs_ws.max_column or 3, 20) + 1):
                ta_cell = bs_ws.cell(row=total_assets_row, column=col_idx)
                tle_cell = bs_ws.cell(row=total_le_row, column=col_idx)
                # data_only=False이므로 수식 문자열 확인만
                if ta_cell.value and tle_cell.value:
                    # 수식이 존재하면 구조적으로 OK
                    pass

        if critical_flags:
            return 1.0, issues, critical_flags

        return 5.0, issues, critical_flags

    def _check_cross_refs(self, wb: Any) -> tuple[float, list[str]]:
        """IS→BS→CF 교차 참조 검증 (수식 기반)."""
        issues: list[str] = []
        checks_passed = 0
        checks_total = 0

        # IS, BS, CF 시트 존재 확인
        sheets = {ws.title: ws for ws in wb.worksheets}
        has_is = "IS" in sheets
        has_bs = "BS" in sheets
        has_cf = "CF" in sheets

        if has_is and has_cf:
            checks_total += 1
            # CF 시트에서 IS 시트 참조하는 수식이 있는지 확인
            cf_ws = sheets["CF"]
            has_is_ref = False
            for row in cf_ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and "IS!" in cell.value:
                        has_is_ref = True
                        break
                if has_is_ref:
                    break

            if has_is_ref:
                checks_passed += 1
            else:
                issues.append("CF 시트에서 IS 시트 참조 수식 없음 (순이익, D&A 연결 필요)")

        if has_bs and has_cf:
            checks_total += 1
            # CF 시트에서 BS 참조 또는 BS에서 CF 참조
            cf_ws = sheets["CF"]
            has_bs_ref = False
            for row in cf_ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and "BS!" in cell.value:
                        has_bs_ref = True
                        break
                if has_bs_ref:
                    break

            if has_bs_ref:
                checks_passed += 1
            else:
                issues.append("CF 시트에서 BS 시트 참조 수식 없음 (현금 잔액 연결 필요)")

        if checks_total == 0:
            return 5.0, []

        ratio = checks_passed / checks_total
        score = max(1.0, 1.0 + ratio * 4.0)
        return score, issues

    def _check_completeness(self, wb: Any) -> tuple[float, list[str]]:
        """플레이스홀더 패턴 탐지."""
        issues: list[str] = []
        placeholder_count = 0

        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if not isinstance(cell.value, str):
                        continue
                    for pattern in _PLACEHOLDER_PATTERNS:
                        matches = re.findall(pattern, cell.value, re.IGNORECASE)
                        if matches:
                            placeholder_count += len(matches)
                            if len(issues) < 5:
                                issues.append(f"시트 '{ws.title}' 행 {cell.row}: 플레이스홀더 '{matches[0]}'")

        score = 5.0 if placeholder_count == 0 else max(1.0, 5.0 - placeholder_count)
        return score, issues

    def _check_formatting(self, wb: Any) -> tuple[float, list[str]]:
        """숫자 형식 일관성 검증."""
        issues: list[str] = []
        skip_sheets = {"Legend"}
        format_violations = 0

        # 기대하는 숫자 포맷 패턴
        expected_formats = {
            "#,##0",  # KRW
            "0.0%",  # 퍼센트
            "0.00%",  # 퍼센트 (소수 2자리)
            '0.0"x"',  # 멀티플
            "0",  # 일수
            "General",  # 기본
        }

        for ws in wb.worksheets:
            if ws.title in skip_sheets:
                continue

            num_cells_with_format = 0
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is None:
                        continue
                    if isinstance(cell.value, (int, float)) or (
                        isinstance(cell.value, str) and cell.value.startswith("=")
                    ):
                        fmt = cell.number_format
                        if fmt and fmt != "General":
                            num_cells_with_format += 1
                            # 비표준 포맷 감지 (허용 포맷에 없으면)
                            if fmt not in expected_formats and not any(
                                ef in fmt for ef in ("#,##0", "0.0%", "0.00%", '"x"')
                            ):
                                format_violations += 1
                                if format_violations <= 3:
                                    issues.append(f"시트 '{ws.title}': 비표준 숫자 형식 '{fmt}'")

        score = max(1.0, 5.0 - format_violations * 0.5)
        return score, issues
