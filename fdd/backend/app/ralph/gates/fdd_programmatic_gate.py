"""FDD Programmatic Gate — 비용 $0, 밀리초 단위 구조/수치 검증.

7개 차원:
1. numerical_consistency (23%) — IR 텍스트 내 수치가 엔진 결과와 일치
2. evidence_coverage (18%) — ClaimBlock의 evidence_refs 존재
3. placeholder_absence (13%) — [INSERT], [TBD] 등 플레이스홀더 부재
4. structure_completeness (13%) — 필수 섹션 존재
5. checklist_alignment (8%) — (Pass 2) CORRECTED 항목 반영 여부
6. financial_statement_quality (15%) — IS/BS 시트 커버리지 + 일관성 + 소계검증
7. industry_account_coverage (10%) — 산업별 필수 계정 존재 여부
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate

# 플레이스홀더 패턴
_PLACEHOLDER_PATTERNS = [
    r"\[INSERT\]",
    r"\[TBD\]",
    r"\[TODO\]",
    r"__+",
    r"\{[A-Z_]+\}",
    r"\[FILL\]",
    r"\[PLACEHOLDER\]",
]
_PLACEHOLDER_RE = re.compile("|".join(_PLACEHOLDER_PATTERNS), re.IGNORECASE)

# 금액 패턴 (한국 원화 기준: 숫자 + 콤마)
_NUMBER_RE = re.compile(r"-?[\d,]+(?:\.\d+)?")


class FDDProgrammaticGate(QualityGate):
    """FDD Report IR 프로그래밍 검증 Gate (Gate 1)."""

    def __init__(
        self,
        checklist_corrections: list[dict[str, Any]] | None = None,
    ) -> None:
        self._checklist_corrections = checklist_corrections or []

    @property
    def name(self) -> str:
        return "fdd_programmatic"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        """블록 JSON을 프로그래밍으로 검증한다.

        Args:
            artifact_path: Refined 블록 JSON 문자열
            prd_section: PRD 섹션 (block_type, title 등)
            source_data: 엔진 데이터 (교차 검증용)
        """
        start_ns = time.perf_counter_ns()
        issues: list[str] = []
        suggestions: list[str] = []
        critical_flags: list[str] = []

        # JSON 파싱
        try:
            block = json.loads(artifact_path)
        except json.JSONDecodeError:
            return self._timed_result(
                start_ns,
                dimensions=[DimensionScore("json_valid", "JSON 유효성", 0.0, 1.0, "Invalid JSON")],
                issues=["Artifact is not valid JSON"],
                suggestions=["Ensure LLM returns valid JSON"],
                critical_flags=["INVALID_JSON"],
            )

        block_type = block.get("type", "")
        source = source_data or {}

        # 1. 수치 정합성 (25%)
        num_score, num_issues = self._check_numerical_consistency(block, source)

        # 2. 근거 참조 (20%)
        ev_score, ev_issues = self._check_evidence_coverage(block)

        # 3. 플레이스홀더 부재 (15%)
        ph_score, ph_issues = self._check_placeholder_absence(block)

        # 4. 구조 완전성 (15%)
        struct_score, struct_issues = self._check_structure_completeness(block, block_type)

        # 5. 체크리스트 정렬 (10%)
        cl_score, cl_issues = self._check_checklist_alignment(block)

        # 6. 재무제표 품질 (15%)
        fs_score, fs_issues = self._check_financial_statement_quality(block, source)

        # 7. 산업별 계정 커버리지 (10%)
        ind_score, ind_issues = self._check_industry_account_coverage(block, source)

        issues.extend(num_issues)
        issues.extend(ev_issues)
        issues.extend(ph_issues)
        issues.extend(struct_issues)
        issues.extend(cl_issues)
        issues.extend(fs_issues)
        issues.extend(ind_issues)

        dimensions = [
            DimensionScore("numerical_consistency", "수치 정합성", num_score, 0.23,
                           "; ".join(num_issues) if num_issues else "OK"),
            DimensionScore("evidence_coverage", "근거 참조", ev_score, 0.18,
                           "; ".join(ev_issues) if ev_issues else "OK"),
            DimensionScore("placeholder_absence", "플레이스홀더 부재", ph_score, 0.13,
                           "; ".join(ph_issues) if ph_issues else "OK"),
            DimensionScore("structure_completeness", "구조 완전성", struct_score, 0.13,
                           "; ".join(struct_issues) if struct_issues else "OK"),
            DimensionScore("checklist_alignment", "체크리스트 정렬", cl_score, 0.08,
                           "; ".join(cl_issues) if cl_issues else "OK"),
            DimensionScore("financial_statement_quality", "재무제표 품질", fs_score, 0.15,
                           "; ".join(fs_issues) if fs_issues else "OK"),
            DimensionScore("industry_account_coverage", "산업별 계정 커버리지", ind_score, 0.10,
                           "; ".join(ind_issues) if ind_issues else "OK"),
        ]

        return self._timed_result(
            start_ns, dimensions, issues, suggestions, critical_flags,
        )

    # ── Dimension Checkers ───────────────────────────────────────────────

    def _check_numerical_consistency(
        self, block: dict, source: dict,
    ) -> tuple[float, list[str]]:
        """텍스트 내 수치가 엔진 데이터와 일치하는지 검증."""
        issues: list[str] = []

        # 블록 텍스트 추출
        text_parts = self._extract_text(block)
        if not text_parts:
            return 5.0, []

        full_text = " ".join(text_parts)
        numbers_in_text = set(_NUMBER_RE.findall(full_text))

        # 소스 데이터에서 수치 추출
        source_numbers = set()
        self._collect_numbers(source, source_numbers)

        if not source_numbers:
            return 5.0, []  # 비교 대상 없음

        # 텍스트의 수치가 소스에 있는지
        mismatches = 0
        for num_str in numbers_in_text:
            clean = num_str.replace(",", "")
            try:
                val = float(clean)
            except ValueError:
                continue
            if not self._is_monetary_candidate(val, num_str, full_text):
                continue  # 비금액 숫자(연도, 퍼센트 등) 무시
            # 소스에 근사치가 있는지 확인
            found = any(abs(float(sn.replace(",", "")) - val) < 1.0 for sn in source_numbers
                        if self._safe_float(sn) is not None)
            if not found:
                mismatches += 1
                issues.append(f"Number {num_str} not found in engine data")

        if mismatches == 0:
            return 5.0, issues
        elif mismatches <= 2:
            return 3.5, issues
        else:
            return 2.0, issues

    def _check_evidence_coverage(self, block: dict) -> tuple[float, list[str]]:
        """ClaimBlock의 evidence_refs 존재 여부."""
        issues: list[str] = []
        if block.get("type") != "claim":
            return 5.0, []

        refs = block.get("evidence_refs", [])
        if not refs:
            issues.append("ClaimBlock has no evidence_refs — unverified claim")
            return 1.0, issues

        return 5.0, []

    def _check_placeholder_absence(self, block: dict) -> tuple[float, list[str]]:
        """플레이스홀더 패턴이 텍스트에 없는지 검증."""
        issues: list[str] = []
        text_parts = self._extract_text(block)
        full_text = " ".join(text_parts)

        matches = _PLACEHOLDER_RE.findall(full_text)
        if matches:
            issues.append(f"Placeholders found: {', '.join(set(matches))}")
            return max(1.0, 5.0 - len(matches) * 1.5), issues

        return 5.0, []

    def _check_structure_completeness(
        self, block: dict, block_type: str,
    ) -> tuple[float, list[str]]:
        """필수 필드 존재 확인."""
        issues: list[str] = []
        required: dict[str, list[str]] = {
            "text": ["content"],
            "claim": ["claim_text"],
            "issue": ["issues"],
        }

        reqs = required.get(block_type, [])
        missing = [f for f in reqs if not block.get(f)]
        if missing:
            issues.append(f"Missing required fields: {', '.join(missing)}")
            return 2.0, issues

        # 텍스트 길이 검증 (최소 50자)
        text_parts = self._extract_text(block)
        total_len = sum(len(t) for t in text_parts)
        if total_len < 50:
            issues.append(f"Content too short ({total_len} chars, min 50)")
            return 3.0, issues

        return 5.0, []

    def _check_checklist_alignment(self, block: dict) -> tuple[float, list[str]]:
        """Pass 2: CORRECTED 항목 수정값이 텍스트에 반영되었는지."""
        if not self._checklist_corrections:
            return 5.0, []

        issues: list[str] = []
        text_parts = self._extract_text(block)
        full_text = " ".join(text_parts).lower()

        corrected_items = [c for c in self._checklist_corrections if c.get("status") == "CORRECTED"]
        if not corrected_items:
            return 5.0, []

        reflected = 0
        for item in corrected_items:
            correction = (item.get("user_correction") or "").lower()
            amount = (item.get("user_amount") or "").replace(",", "")
            # 키워드 기반 매칭: 의미 있는 단어(2자 이상)의 60%+ 존재 시 반영으로 판정
            if (correction and self._correction_reflected(correction, full_text)) or (amount and amount in full_text.replace(",", "")):
                reflected += 1

        if not corrected_items:
            return 5.0, []

        ratio = reflected / len(corrected_items)
        if ratio >= 0.8:
            return 5.0, issues
        elif ratio >= 0.5:
            issues.append(f"Only {reflected}/{len(corrected_items)} corrections reflected")
            return 3.5, issues
        else:
            issues.append(f"Only {reflected}/{len(corrected_items)} corrections reflected — major gaps")
            return 2.0, issues

    def _check_financial_statement_quality(
        self, block: dict, source: dict,
    ) -> tuple[float, list[str]]:
        """재무제표(IS/BS) 시트 커버리지 + 일관성 검증.

        source_data에 financial_statements 정보가 있을 때만 검증:
          source_data = {
            "financial_statements": {
              "sheets": ["IS", "BS", "CF"],
              "is_line_count": 15,
              "bs_line_count": 20,
              "has_subtotals": True,
              "net_income": 1500,
              "retained_earnings_delta": 1500,
              "total_assets": 10000,
              "total_liabilities_equity": 10000,
            }
          }
        """
        fs_data = source.get("financial_statements")
        if not fs_data:
            return 5.0, []  # FS 데이터 없으면 스킵

        issues: list[str] = []
        score = 5.0

        # 시트 커버리지
        sheets = [s.upper() for s in fs_data.get("sheets", [])]
        if "IS" not in sheets:
            issues.append("Income Statement sheet missing")
            score -= 1.5
        if "BS" not in sheets:
            issues.append("Balance Sheet sheet missing")
            score -= 1.5

        # 최소 항목 수
        is_count = fs_data.get("is_line_count", 0)
        bs_count = fs_data.get("bs_line_count", 0)
        if is_count < 8:
            issues.append(f"IS has only {is_count} line items (min 8)")
            score -= 0.5
        if bs_count < 12:
            issues.append(f"BS has only {bs_count} line items (min 12)")
            score -= 0.5

        # 소계 포함 여부
        if not fs_data.get("has_subtotals", False):
            issues.append("Financial statements lack subtotal rows")
            score -= 0.5

        # Cross-sheet 일관성: IS Net Income ≈ BS Retained Earnings 변동
        net_income = fs_data.get("net_income")
        re_delta = fs_data.get("retained_earnings_delta")
        if net_income is not None and re_delta is not None:
            try:
                diff = abs(float(net_income) - float(re_delta))
                if diff > 1.0:  # 1백만원 이상 차이
                    issues.append(
                        f"IS Net Income ({net_income}) != BS RE delta ({re_delta})"
                    )
                    score -= 1.0
            except (ValueError, TypeError):
                pass

        # BS 균형: Total Assets = Total Liabilities + Equity
        total_assets = fs_data.get("total_assets")
        total_le = fs_data.get("total_liabilities_equity")
        if total_assets is not None and total_le is not None:
            try:
                diff = abs(float(total_assets) - float(total_le))
                if diff > 1.0:
                    issues.append(
                        f"BS imbalance: Assets ({total_assets}) != L+E ({total_le})"
                    )
                    score -= 1.0
            except (ValueError, TypeError):
                pass

        # 소계→합계 일치 검증
        # subtotal_totals: list[{"label": str, "subtotals_sum": float, "total": float}]
        for st_check in fs_data.get("subtotal_totals", []):
            try:
                st_sum = float(st_check.get("subtotals_sum", 0))
                total_val = float(st_check.get("total", 0))
                label = st_check.get("label", "unknown")
                diff = abs(st_sum - total_val)
                # 절대 오차(1백만원) 또는 상대 오차(0.1%) 중 하나라도 초과 시
                rel_threshold = abs(total_val) * 0.001 if total_val else 0.0
                tolerance = max(1.0, rel_threshold)
                if diff > tolerance:
                    issues.append(
                        f"Subtotal mismatch in {label}: "
                        f"sum of subtotals ({st_sum:,.0f}) != total ({total_val:,.0f})"
                    )
                    score -= 0.5
            except (ValueError, TypeError):
                continue

        return max(1.0, score), issues

    def _check_industry_account_coverage(
        self, block: dict, source: dict,
    ) -> tuple[float, list[str]]:
        """산업별 필수 계정 존재 여부 검증.

        source_data에 industry_type과 account_names가 있을 때 검증:
          source_data = {
            "industry_type": "manufacturing" | "service" | "retail" | ...,
            "account_names": ["매출액", "매출원가", "급여", ...]
          }

        industry_type이 없으면 범용(common) 기본 세트로 검증.
        """
        account_names = source.get("account_names", [])
        if not account_names:
            return 5.0, []  # 계정 데이터 없으면 스킵

        industry = source.get("industry_type", "common")
        issues: list[str] = []

        # 산업별 필수 계정 매핑 (한글/영문 혼합)
        required_accounts: dict[str, list[list[str]]] = {
            "common": [
                ["매출액", "revenue", "sales"],
                ["매출원가", "cost of sales", "cogs"],
                ["판매비와관리비", "판관비", "sg&a", "selling"],
                ["영업이익", "operating income", "operating profit"],
                ["당기순이익", "net income", "net profit"],
                ["유동자산", "current assets"],
                ["유동부채", "current liabilities"],
                ["자본총계", "equity", "total equity"],
            ],
            "manufacturing": [
                ["매출액", "revenue", "sales"],
                ["매출원가", "cost of sales", "cogs"],
                ["재고자산", "inventory", "inventories"],
                ["유형자산", "ppe", "property", "fixed assets"],
                ["감가상각비", "depreciation"],
                ["원재료", "raw material"],
                ["영업이익", "operating income", "operating profit"],
                ["당기순이익", "net income"],
            ],
            "service": [
                ["매출액", "revenue", "sales"],
                ["인건비", "급여", "salary", "wages", "personnel"],
                ["판매비와관리비", "판관비", "sg&a"],
                ["매출채권", "accounts receivable", "receivable"],
                ["선수금", "선수수익", "deferred revenue", "unearned"],
                ["영업이익", "operating income", "operating profit"],
                ["당기순이익", "net income"],
            ],
            "retail": [
                ["매출액", "revenue", "sales"],
                ["매출원가", "cost of sales", "cogs"],
                ["재고자산", "inventory", "inventories"],
                ["매출채권", "accounts receivable"],
                ["매입채무", "accounts payable"],
                ["영업이익", "operating income", "operating profit"],
                ["당기순이익", "net income"],
            ],
        }

        # 산업 타입이 매핑에 없으면 common 사용
        required = required_accounts.get(industry, required_accounts["common"])
        account_set = {name.lower().strip() for name in account_names}

        missing = []
        for synonyms in required:
            found = any(
                syn.lower() in account_set  # 정확 매칭 (substring 아님)
                for syn in synonyms
            )
            if not found:
                missing.append(synonyms[0])  # 첫 번째 이름을 대표로

        if not missing:
            return 5.0, issues

        coverage = (len(required) - len(missing)) / len(required)
        if coverage >= 0.8:
            # 1~2개 누락: 경미
            score = 4.0
        elif coverage >= 0.6:
            score = 3.0
        else:
            score = 2.0

        issues.append(
            f"Industry({industry}) missing accounts: {', '.join(missing)} "
            f"({len(missing)}/{len(required)} not found)"
        )
        return score, issues

    # ── Helpers ──────────────────────────────────────────────────────────

    def _extract_text(self, block: dict) -> list[str]:
        """블록에서 텍스트 부분을 추출한다."""
        parts: list[str] = []
        if block.get("content"):
            parts.append(block["content"])
        if block.get("claim_text"):
            parts.append(block["claim_text"])
        for bp in block.get("bullet_points", []):
            parts.append(bp)
        for issue in block.get("issues", []):
            if isinstance(issue, dict):
                parts.append(issue.get("description", ""))
                parts.append(issue.get("recommendation", ""))
        return parts

    def _collect_numbers(self, data: Any, numbers: set) -> None:
        """재귀적으로 dict/list에서 숫자 문자열을 수집한다."""
        if isinstance(data, dict):
            for v in data.values():
                self._collect_numbers(v, numbers)
        elif isinstance(data, list):
            for item in data:
                self._collect_numbers(item, numbers)
        elif isinstance(data, str):
            for m in _NUMBER_RE.findall(data):
                if len(m) >= 3:  # 의미 있는 숫자만
                    numbers.add(m)

    # 연도 범위 (1900~2100)
    _YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
    # 퍼센트 인접 패턴 (숫자 직후 % 또는 퍼센트/포인트)
    _PERCENT_SUFFIX_RE = re.compile(r"[%％]|퍼센트|포인트|percent|pp|bps|bp")

    def _is_monetary_candidate(self, val: float, num_str: str, context: str) -> bool:
        """숫자가 금액일 가능성이 있는지 판정.

        연도(1900-2100), 퍼센트 인접 숫자, 사소한 숫자(<10)를 제외한다.
        """
        # 절대값 10 미만: 사소한 숫자
        if abs(val) < 10:
            return False

        # 연도 필터: 1900~2100 범위 정수
        if val == int(val) and 1900 <= int(val) <= 2100:
            return False

        # 퍼센트 인접: 숫자 직후에 %/퍼센트/포인트/bps가 오는 경우
        idx = context.find(num_str)
        if idx >= 0:
            after = context[idx + len(num_str):idx + len(num_str) + 10]
            if self._PERCENT_SUFFIX_RE.search(after):
                return False

        return True

    # 수정 텍스트에서 무시할 한국어 불용어
    _STOP_WORDS = frozenset({
        "이", "가", "을", "를", "에", "의", "로", "으로", "와", "과",
        "는", "은", "도", "만", "까지", "부터", "에서", "한", "할", "하는",
        "것", "수", "등", "및", "또는", "그", "이것", "저것",
    })

    def _correction_reflected(self, correction: str, full_text: str) -> bool:
        """수정 텍스트의 키워드가 본문에 충분히 반영되었는지 판정.

        단순 substring 매칭 대신, 2자 이상 의미 있는 단어를 추출하여
        60% 이상 존재하면 반영된 것으로 판정한다.
        """
        # 한국어/영문 단어 토큰화 (2자 이상)
        words = re.findall(r"[가-힣a-z]{2,}", correction)
        keywords = [w for w in words if w not in self._STOP_WORDS]

        if not keywords:
            # 키워드 추출 불가 시 원본 substring 매칭 (빈 수정 텍스트 방어)
            return len(correction) >= 4 and correction in full_text

        matched = sum(1 for kw in keywords if kw in full_text)
        return matched / len(keywords) >= 0.6

    def _safe_float(self, s: str) -> float | None:
        try:
            return float(s.replace(",", ""))
        except (ValueError, AttributeError):
            return None
