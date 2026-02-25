"""DOCX Programmatic Gate — python-docx 기반 LDD 보고서 프로그래밍 검증.

Phase 2(섹션별 반복 개선)에서는 JSON 검증 모드로 동작하고,
Phase 3(통합 검증)에서는 DOCX 파일 검증 모드로 동작한다.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate

# JSON 검증용 필수 필드
_REQUIRED_ITEM_FIELDS = {"status", "description"}
_VALID_STATUSES = {"OK", "ISSUE", "NA", "PENDING"}
_VALID_ISSUE_LEVELS = {"CRITICAL", "HIGH", "MEDIUM", "LOW", None}
_VALID_RFI_PREFIXES = {"CORP", "CAP", "CONTRACT", "LIT", "LABOR", "IP", "RE", "PERMIT", "TAX", "IT"}


class DOCXProgrammaticGate(QualityGate):
    """LDD 보고서 프로그래밍 검증 게이트.

    두 가지 모드로 동작:
    - **JSON 모드**: Phase 2에서 generate_section()이 반환하는 JSON 문자열 검증
    - **DOCX 모드**: Phase 3에서 assemble_document()이 생성한 .docx 파일 검증

    JSON 모드 검증 레이어:
    1. 항목 구조 완전성 (필수 필드, 유효 상태값)
    2. 분석 완전성 (PENDING 비율)
    3. RFI 번호 체계 정합성
    4. 이슈 분류 정확성 (issue_level 유효값)
    5. 근거 충실도 (evidence_refs, confidence)
    6. 리뷰 반영 검증 (Pass 2 전용 — 반려 항목 재분석 여부)

    DOCX 모드 검증 레이어:
    1. 섹션 구조 검증 (목차, 섹션 번호 정합성)
    2. 이슈 카운트 정합성 (본문 이슈 수 vs 집계)
    3. RFI 번호 체계 검증 (CORP-001 형식)
    4. 법률 용어 패턴 매칭
    5. 텍스트 완전성 (플레이스홀더 부재)
    """

    def __init__(self, user_reviews: dict[str, dict] | None = None) -> None:
        """DOCXProgrammaticGate를 초기화한다.

        Args:
            user_reviews: Pass 2에서 전달하는 사용자 리뷰 정보.
                {item_id: {"approved": bool, "feedback": str}}
                None이면 review_alignment 차원을 건너뛴다 (Pass 1).
        """
        self._user_reviews = user_reviews

    @property
    def name(self) -> str:
        return "docx_programmatic"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        # artifact_path가 .docx 파일인지 JSON 문자열인지 판별
        if self._is_json_artifact(artifact_path):
            return await self._evaluate_json(artifact_path, prd_section, source_data)
        return await self._evaluate_docx(artifact_path, prd_section, source_data)

    # ── JSON 모드 (Phase 2) ──────────────────────────────────────────────────

    @staticmethod
    def _is_json_artifact(artifact_path: str) -> bool:
        """artifact가 JSON 문자열인지 파일 경로인지 판별한다."""
        stripped = artifact_path.strip()
        # JSON 배열 또는 객체로 시작하면 JSON
        if stripped.startswith("[") or stripped.startswith("{"):
            return True
        # .docx 확장자이거나 실제 파일이 존재하면 DOCX
        if stripped.endswith(".docx") or Path(stripped).is_file():
            return False
        # 그 외 JSON 파싱 시도
        try:
            json.loads(stripped)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    async def _evaluate_json(
        self,
        artifact_json: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        """Phase 2 JSON 검증 — 섹션별 분석 결과 JSON을 검증한다."""
        start = time.perf_counter_ns()
        issues: list[str] = []
        suggestions: list[str] = []
        critical_flags: list[str] = []

        try:
            items = json.loads(artifact_json)
            if not isinstance(items, list):
                items = [items]
        except json.JSONDecodeError as exc:
            return self._timed_result(
                start, [], [f"JSON 파싱 실패: {exc}"], [], [],
            )

        if not items:
            return self._timed_result(
                start, [], ["빈 분석 결과"], ["항목 분석을 수행하세요"], [],
            )

        # 1. 항목 구조 완전성
        struct_score, struct_issues = self._check_json_structure(items)
        issues.extend(struct_issues)

        # 2. 분석 완전성 (PENDING 비율)
        analysis_score, analysis_issues = self._check_analysis_completeness(items)
        issues.extend(analysis_issues)

        # 3. RFI 번호 체계
        rfi_score, rfi_issues = self._check_json_rfi(items)
        issues.extend(rfi_issues)

        # 4. 이슈 분류 정확성
        classify_score, classify_issues = self._check_issue_classification(items)
        issues.extend(classify_issues)

        # 5. 근거 충실도
        evidence_score, evidence_issues = self._check_evidence_quality(items)
        issues.extend(evidence_issues)

        # 6. 리뷰 반영 검증 (Pass 2 전용)
        review_score = None
        if self._user_reviews:
            review_score, review_issues = self._check_review_alignment(items)
            issues.extend(review_issues)

        # 가중치: user_reviews가 있으면 review_alignment(0.10) 추가, 기존 가중치 재조정
        if review_score is not None:
            dimensions = [
                DimensionScore("json_structure", "항목 구조", struct_score, 0.15),
                DimensionScore("analysis_completeness", "분석 완전성", analysis_score, 0.25),
                DimensionScore("rfi_numbering", "RFI 번호 체계", rfi_score, 0.15),
                DimensionScore("issue_classification", "이슈 분류", classify_score, 0.15),
                DimensionScore("evidence_quality", "근거 충실도", evidence_score, 0.20),
                DimensionScore("review_alignment", "리뷰 반영", review_score, 0.10),
            ]
        else:
            dimensions = [
                DimensionScore("json_structure", "항목 구조", struct_score, 0.20),
                DimensionScore("analysis_completeness", "분석 완전성", analysis_score, 0.30),
                DimensionScore("rfi_numbering", "RFI 번호 체계", rfi_score, 0.15),
                DimensionScore("issue_classification", "이슈 분류", classify_score, 0.15),
                DimensionScore("evidence_quality", "근거 충실도", evidence_score, 0.20),
            ]

        if suggestions or issues:
            suggestions.append("위 이슈들을 수정 후 재검증하세요.")

        return self._timed_result(
            start, dimensions, issues, suggestions, critical_flags,
        )

    def _check_json_structure(self, items: list[dict]) -> tuple[float, list[str]]:
        """각 항목의 필수 필드 존재 여부."""
        issues: list[str] = []
        missing_count = 0

        for i, item in enumerate(items):
            for field in _REQUIRED_ITEM_FIELDS:
                if field not in item:
                    missing_count += 1
                    issues.append(f"항목 {i}: 필수 필드 '{field}' 누락")

            status = item.get("status")
            if status and status not in _VALID_STATUSES:
                issues.append(f"항목 {i}: 유효하지 않은 상태값 '{status}'")

        score = max(1.0, 5.0 - missing_count * 0.5)
        return score, issues

    def _check_analysis_completeness(self, items: list[dict]) -> tuple[float, list[str]]:
        """PENDING 상태 비율 확인."""
        issues: list[str] = []
        total = len(items)
        pending = sum(1 for it in items if it.get("status") == "PENDING")

        if total > 0:
            pending_ratio = pending / total
            if pending_ratio > 0.5:
                issues.append(f"미분석 항목 과다: {pending}/{total} ({pending_ratio:.0%})")
            elif pending_ratio > 0.2:
                issues.append(f"일부 항목 미분석: {pending}/{total}")

        analyzed = total - pending
        score = (analyzed / max(total, 1)) * 5.0
        return max(1.0, score), issues

    def _check_json_rfi(self, items: list[dict]) -> tuple[float, list[str]]:
        """JSON 내 RFI 번호 체계 검증."""
        issues: list[str] = []
        rfi_numbers: list[str] = []

        for item in items:
            rfi = item.get("rfi_number", "")
            if not rfi:
                continue
            rfi_numbers.append(rfi)

            # 형식 체크
            rfi_pattern = re.compile(r"^([A-Z]+)-(\d{2,3})$")
            m = rfi_pattern.match(rfi)
            if not m:
                issues.append(f"잘못된 RFI 형식: '{rfi}' (예: CORP-001)")
                continue

            prefix = m.group(1)
            if prefix not in _VALID_RFI_PREFIXES:
                issues.append(f"유효하지 않은 RFI 접두사: '{rfi}'")

        # 중복 체크
        seen: set[str] = set()
        for rfi in rfi_numbers:
            if rfi in seen:
                issues.append(f"중복 RFI 번호: {rfi}")
            seen.add(rfi)

        score = max(1.0, 5.0 - len(issues) * 0.5)
        return score, issues

    def _check_issue_classification(self, items: list[dict]) -> tuple[float, list[str]]:
        """이슈 분류 정확성."""
        issues: list[str] = []
        issue_items = [it for it in items if it.get("status") == "ISSUE"]

        for item in issue_items:
            level = item.get("issue_level")
            if level not in _VALID_ISSUE_LEVELS:
                issues.append(f"유효하지 않은 이슈 레벨: '{level}'")

            if not item.get("deal_impact"):
                issues.append(f"ISSUE 항목에 deal_impact 미기재: {item.get('item_id', '?')}")

            if not item.get("recommendation"):
                issues.append(f"ISSUE 항목에 recommendation 미기재: {item.get('item_id', '?')}")

        score = max(1.0, 5.0 - len(issues) * 0.5)
        return score, issues

    def _check_evidence_quality(self, items: list[dict]) -> tuple[float, list[str]]:
        """근거 충실도 (confidence, evidence_refs)."""
        issues: list[str] = []
        low_confidence = 0

        for item in items:
            if item.get("status") == "PENDING":
                continue

            confidence = item.get("confidence", 0.0)
            if isinstance(confidence, (int, float)) and confidence < 0.3:
                low_confidence += 1

        if low_confidence > len(items) * 0.5:
            issues.append(f"저신뢰도 항목 과다: {low_confidence}/{len(items)}")

        score = max(1.0, 5.0 - low_confidence * 0.3)
        return score, issues

    def _check_review_alignment(self, items: list[dict]) -> tuple[float, list[str]]:
        """Pass 2 리뷰 반영 검증 — 반려된 항목이 재분석되었는지 확인한다."""
        issues: list[str] = []
        if not self._user_reviews:
            return 5.0, issues

        rejected_ids = {
            item_id for item_id, review in self._user_reviews.items()
            if not review.get("approved", True)
        }

        if not rejected_ids:
            return 5.0, issues

        # 분석 결과에서 반려 항목 확인
        result_ids = {item.get("item_id", "") for item in items}
        missing_reanalysis = rejected_ids - result_ids

        if missing_reanalysis:
            issues.append(
                f"반려 항목 {len(missing_reanalysis)}건 재분석 누락: "
                f"{', '.join(sorted(missing_reanalysis)[:5])}"
            )

        # 반려 항목 중 여전히 PENDING인 것 확인
        still_pending = 0
        for item in items:
            item_id = item.get("item_id", "")
            if item_id in rejected_ids and item.get("status") == "PENDING":
                still_pending += 1

        if still_pending:
            issues.append(f"반려 항목 중 {still_pending}건이 여전히 PENDING 상태")

        # 점수 계산: 반려 항목 중 제대로 재분석된 비율
        total_rejected = len(rejected_ids)
        reanalyzed = total_rejected - len(missing_reanalysis) - still_pending
        ratio = reanalyzed / max(total_rejected, 1)
        score = max(1.0, ratio * 5.0)

        return score, issues

    # ── DOCX 모드 (Phase 3) ──────────────────────────────────────────────────

    async def _evaluate_docx(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        """Phase 3 DOCX 검증 — 최종 생성된 .docx 파일을 검증한다."""
        start = time.perf_counter_ns()
        issues: list[str] = []
        suggestions: list[str] = []
        critical_flags: list[str] = []

        try:
            from docx import Document
            doc = Document(artifact_path)
        except Exception as exc:
            return self._timed_result(
                start, [], [f"DOCX 로드 실패: {exc}"], [], [f"DOCX 파일 손상: {exc}"],
            )

        # 전체 텍스트 추출
        full_text = "\n".join(p.text for p in doc.paragraphs)
        all_tables = doc.tables

        # 1. 섹션 구조 검증
        struct_score, struct_issues = self._check_structure(doc, prd_section)
        issues.extend(struct_issues)

        # 2. 이슈 카운트 정합성
        count_score, count_issues = self._check_issue_counts(full_text, prd_section)
        issues.extend(count_issues)

        # 3. RFI 번호 체계 검증
        rfi_score, rfi_issues = self._check_rfi_numbering(full_text)
        issues.extend(rfi_issues)

        # 4. 법률 용어 패턴 매칭
        legal_score, legal_issues = self._check_legal_terms(full_text)
        issues.extend(legal_issues)

        # 5. 텍스트 완전성
        complete_score, complete_issues = self._check_completeness(full_text)
        issues.extend(complete_issues)
        if any("CRITICAL" in i for i in complete_issues):
            critical_flags.extend([i for i in complete_issues if "CRITICAL" in i])

        dimensions = [
            DimensionScore("structure", "섹션 구조", struct_score, 0.25),
            DimensionScore("issue_counts", "이슈 정합성", count_score, 0.25),
            DimensionScore("rfi_numbering", "RFI 번호 체계", rfi_score, 0.15),
            DimensionScore("legal_terms", "법률 용어", legal_score, 0.15),
            DimensionScore("completeness", "텍스트 완전성", complete_score, 0.20),
        ]

        if issues:
            suggestions.append("위 이슈들을 수정 후 재검증하세요.")

        return self._timed_result(
            start, dimensions, issues, suggestions, critical_flags,
        )

    # ── 검증 레이어 ──────────────────────────────────────────────────────────

    def _check_structure(self, doc: Any, prd: dict) -> tuple[float, list[str]]:
        """섹션 구조 검증."""
        issues: list[str] = []
        headings = [p.text.strip() for p in doc.paragraphs if p.style and "Heading" in (p.style.name or "")]

        expected_sections = prd.get("expected_sections", [])
        if expected_sections:
            for exp in expected_sections:
                if not any(exp.lower() in h.lower() for h in headings):
                    issues.append(f"필수 섹션 누락: '{exp}'")

        if not headings:
            issues.append("문서에 제목(Heading) 스타일이 없습니다")
            return 1.0, issues

        score = max(1.0, 5.0 - len(issues) * 0.5)
        return score, issues

    def _check_issue_counts(self, text: str, prd: dict) -> tuple[float, list[str]]:
        """이슈 카운트 정합성."""
        issues: list[str] = []

        # 본문에서 "이슈" 또는 "ISSUE" 패턴 카운트
        issue_pattern = re.compile(r"\b(ISSUE|이슈|RED|AMBER|CRITICAL|HIGH|MEDIUM)\b", re.IGNORECASE)
        found = len(issue_pattern.findall(text))

        expected = prd.get("expected_issue_count")
        if expected is not None and abs(found - expected) > 5:
            issues.append(f"이슈 카운트 불일치: 본문 {found}건 vs 예상 {expected}건")

        score = 5.0 if not issues else 3.0
        return score, issues

    def _check_rfi_numbering(self, text: str) -> tuple[float, list[str]]:
        """RFI 번호 체계 검증 (CORP-001, CONTRACT-015 형식)."""
        issues: list[str] = []

        rfi_pattern = re.compile(r"\b([A-Z]+-\d{2,3})\b")
        rfis = rfi_pattern.findall(text)

        # 중복 번호 체크
        seen: set[str] = set()
        for rfi in rfis:
            if rfi in seen:
                issues.append(f"중복 RFI 번호: {rfi}")
            seen.add(rfi)

        # 유효 접두사 체크
        valid_prefixes = {"CORP", "CAP", "CONTRACT", "LIT", "LABOR", "IP", "RE", "PERMIT", "TAX", "IT"}
        for rfi in rfis:
            prefix = rfi.split("-")[0]
            if prefix not in valid_prefixes:
                issues.append(f"유효하지 않은 RFI 접두사: {rfi}")

        score = max(1.0, 5.0 - len(issues) * 0.5)
        return score, issues

    def _check_legal_terms(self, text: str) -> tuple[float, list[str]]:
        """법률 용어 정확성 패턴 매칭."""
        issues: list[str] = []

        # 흔한 오타/부정확한 용어 패턴
        error_patterns = [
            (r"진술보증", "올바른 용어: '진술보장' (진술 및 보장)"),
            (r"선행조건(?!.*condition)", "선행조건 영문 병기 권장: 'CP (Condition Precedent)'"),
        ]

        for pattern, msg in error_patterns:
            if re.search(pattern, text):
                issues.append(msg)

        score = max(3.0, 5.0 - len(issues) * 0.5)
        return score, issues

    _PLACEHOLDER_PATTERNS = [
        r"\[INSERT\s*(?:HERE)?\]",
        r"\[TBD\]",
        r"\[XXX\]",
        r"\[TODO\]",
        r"\[금액\]",
        r"\[날짜\]",
        r"\[회사명\]",
        r"Lorem\s+ipsum",
        r"__+",  # 밑줄 빈칸
    ]

    def _check_completeness(self, text: str) -> tuple[float, list[str]]:
        """텍스트 완전성 — 플레이스홀더 부재 확인."""
        issues: list[str] = []

        for pattern in self._PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                issues.append(f"CRITICAL: 플레이스홀더 발견 — '{matches[0]}' ({len(matches)}건)")

        score = 5.0 if not issues else 1.0
        return score, issues
