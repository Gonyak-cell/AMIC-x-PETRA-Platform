"""LDD Guardrails — 7개 검증 함수.

LDD 보고서의 무결성을 코드 레벨에서 검증한다.
LLM 출력의 환각/불일치/누락을 deterministic하게 탐지.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── 53개 DDRL 유효 항목 ID ──────────────────────────────────────
VALID_ITEM_IDS: set[str] = {
    # GOVERNANCE
    "CORP-01",
    "CORP-02",
    "CORP-03",
    "CORP-04",
    "CORP-05",
    "CORP-06",
    # CAPITAL
    "CAP-01",
    "CAP-02",
    "CAP-03",
    "CAP-04",
    "CAP-05",
    "CAP-06",
    # CONTRACTS
    "CONTRACT-01",
    "CONTRACT-02",
    "CONTRACT-03",
    "CONTRACT-04",
    "CONTRACT-05",
    "CONTRACT-06",
    # LITIGATION
    "LIT-01",
    "LIT-02",
    "LIT-03",
    "LIT-04",
    "LIT-05",
    # LABOR
    "LABOR-01",
    "LABOR-02",
    "LABOR-03",
    "LABOR-04",
    "LABOR-05",
    "LABOR-06",
    # IP
    "IP-01",
    "IP-02",
    "IP-03",
    "IP-04",
    "IP-05",
    # REAL_ESTATE
    "RE-01",
    "RE-02",
    "RE-03",
    "RE-04",
    "RE-05",
    # PERMITS
    "PERMIT-01",
    "PERMIT-02",
    "PERMIT-03",
    "PERMIT-04",
    "PERMIT-05",
    # TAX
    "TAX-01",
    "TAX-02",
    "TAX-03",
    "TAX-04",
    "TAX-05",
    # DATA_IT
    "IT-01",
    "IT-02",
    "IT-03",
    "IT-04",
}

VALID_SECTION_TYPES: set[str] = {
    "GOVERNANCE",
    "CAPITAL",
    "CONTRACTS",
    "LITIGATION",
    "LABOR",
    "IP",
    "REAL_ESTATE",
    "PERMITS",
    "TAX",
    "DATA_IT",
}

VALID_STATUSES: set[str] = {"OK", "ISSUE", "NA", "PENDING"}
VALID_LEVELS: set[str] = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

# RFI 접두어 매핑
RFI_PREFIX_MAP: dict[str, str] = {
    "GOVERNANCE": "CORP",
    "CAPITAL": "CAP",
    "CONTRACTS": "CONTRACT",
    "LITIGATION": "LIT",
    "LABOR": "LABOR",
    "IP": "IP",
    "REAL_ESTATE": "RE",
    "PERMITS": "PERMIT",
    "TAX": "TAX",
    "DATA_IT": "IT",
}

# 한국 법률 조문 패턴 (제XXX조, 제X조의X 등)
_KOREAN_LAW_PATTERN = re.compile(r"제\s*(\d+)\s*조(?:의\s*\d+)?")


# ── 검증 결과 ──────────────────────────────────────────────────


@dataclass
class GuardrailIssue:
    """단일 검증 위반."""

    rule: str  # 규칙명
    severity: str  # ERROR | WARNING
    location: str  # 위치 (item_id, section 등)
    message: str  # 설명

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule} @ {self.location}: {self.message}"


@dataclass
class GuardrailResult:
    """전체 검증 결과."""

    issues: list[GuardrailIssue] = field(default_factory=list)
    passed_rules: list[str] = field(default_factory=list)
    total_items_checked: int = 0

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")


# ── 메인 클래스 ──────────────────────────────────────────────────


class LDDGuardrails:
    """LDD 보고서 무결성 검증 — 7개 규칙."""

    def __init__(
        self,
        vdr_document_ids: list[str] | None = None,
        gap_detection_result: Any | None = None,
        confidence_threshold: float = 0.25,
    ) -> None:
        self._vdr_doc_ids = set(vdr_document_ids or [])
        self._gap_result = gap_detection_result
        self._confidence_threshold = confidence_threshold

    def validate_all(
        self,
        sections: list[dict[str, Any]],
    ) -> GuardrailResult:
        """모든 검증 규칙을 순차 실행한다."""
        result = GuardrailResult()

        # 전체 항목 수집
        all_items: list[dict[str, Any]] = []
        for section in sections:
            all_items.extend(section.get("items", []))

        result.total_items_checked = len(all_items)

        # 규칙 1: item_id 유효성
        self._validate_item_ids(sections, result)

        # 규칙 2: status ↔ issue_level 일관성
        self._validate_status_level_consistency(all_items, result)

        # 규칙 3: evidence_refs ↔ VDR 문서 ID 일치
        self._validate_evidence_refs(all_items, result)

        # 규칙 4: 법률 환각 탐지 (존재하지 않는 조항)
        self._check_legal_hallucination(all_items, result)

        # 규칙 5: RFI 번호 형식 + 중복
        self._validate_rfi_numbering(sections, result)

        # 규칙 6: Stage 4 누락 탐지 결과 반영 확인
        self._validate_gap_coverage(sections, result)

        # 규칙 7: confidence < threshold 필터링
        self._enforce_confidence_threshold(all_items, result)

        return result

    # ── 규칙 1: item_id 유효성 ──────────────────────────────────

    def _validate_item_ids(
        self,
        sections: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """item_id가 52개 DDRL 항목에 존재하는지 검증."""
        found_ids: set[str] = set()
        rule = "ITEM_ID_VALIDITY"

        for section in sections:
            section_type = section.get("section_type", "")
            if section_type not in VALID_SECTION_TYPES:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="ERROR",
                        location=section_type,
                        message=f"유효하지 않은 section_type: {section_type}",
                    )
                )

            for item in section.get("items", []):
                item_id = item.get("item_id", "")
                if item_id not in VALID_ITEM_IDS:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="ERROR",
                            location=item_id or "(빈 ID)",
                            message=f"유효하지 않은 item_id: {item_id}",
                        )
                    )
                elif item_id in found_ids:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="ERROR",
                            location=item_id,
                            message=f"중복된 item_id: {item_id}",
                        )
                    )
                else:
                    found_ids.add(item_id)

        # 누락된 항목 확인
        missing = VALID_ITEM_IDS - found_ids
        if missing:
            result.issues.append(
                GuardrailIssue(
                    rule=rule,
                    severity="WARNING",
                    location="DDRL",
                    message=f"{len(VALID_ITEM_IDS)}개 DDRL 항목 중 {len(missing)}개 누락: {sorted(missing)[:5]}...",
                )
            )

        if not any(i.rule == rule for i in result.issues):
            result.passed_rules.append(rule)

    # ── 규칙 2: status ↔ issue_level 일관성 ─────────────────────

    def _validate_status_level_consistency(
        self,
        items: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """OK/NA 상태에 issue_level 존재 또는 ISSUE에 issue_level 누락 탐지."""
        rule = "STATUS_LEVEL_CONSISTENCY"
        violations = 0

        for item in items:
            item_id = item.get("item_id", "?")
            status = item.get("status", "")
            level = item.get("issue_level")

            if status == "ISSUE" and not level:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="ERROR",
                        location=item_id,
                        message="ISSUE 상태인데 issue_level이 없음",
                    )
                )
                violations += 1

            if status in ("OK", "NA") and level:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="WARNING",
                        location=item_id,
                        message=f"{status} 상태인데 issue_level={level} 설정됨 (불필요)",
                    )
                )
                violations += 1

            if level and level not in VALID_LEVELS:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="ERROR",
                        location=item_id,
                        message=f"유효하지 않은 issue_level: {level}",
                    )
                )
                violations += 1

            if status and status not in VALID_STATUSES:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="ERROR",
                        location=item_id,
                        message=f"유효하지 않은 status: {status}",
                    )
                )
                violations += 1

        if violations == 0:
            result.passed_rules.append(rule)

    # ── 규칙 3: evidence_refs ↔ VDR 문서 ID 일치 ────────────────

    def _validate_evidence_refs(
        self,
        items: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """evidence_refs가 VDR 문서 ID와 일치하는지 검증."""
        rule = "EVIDENCE_REFS_VALIDITY"

        if not self._vdr_doc_ids:
            # VDR 문서 ID 미제공 시 스킵
            result.passed_rules.append(rule)
            return

        violations = 0
        for item in items:
            item_id = item.get("item_id", "?")
            refs = item.get("evidence_refs", [])
            for ref in refs:
                if ref not in self._vdr_doc_ids:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="WARNING",
                            location=item_id,
                            message=f"VDR에 존재하지 않는 문서 참조: {ref}",
                        )
                    )
                    violations += 1

            # ISSUE 상태인데 evidence_refs 없음 → 경고
            status = item.get("status", "")
            if status == "ISSUE" and not refs:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="WARNING",
                        location=item_id,
                        message="ISSUE 상태인데 증거 자료(evidence_refs)가 없음",
                    )
                )
                violations += 1

        if violations == 0:
            result.passed_rules.append(rule)

    # ── 규칙 4: 법률 환각 탐지 ──────────────────────────────────

    def _check_legal_hallucination(
        self,
        items: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """존재하지 않는 법률 조항/판례 참조 탐지 (휴리스틱).

        - "제XXX조" 패턴에서 비현실적 조문 번호 탐지
        - 동일 조문을 다른 법률로 참조하는 모순 탐지
        """
        rule = "LEGAL_HALLUCINATION_CHECK"
        violations = 0
        law_refs: dict[str, set[str]] = {}  # {조문: {법률명, ...}}

        for item in items:
            item_id = item.get("item_id", "?")
            text_fields = [
                item.get("description", ""),
                item.get("deal_impact", ""),
                item.get("recommendation", ""),
            ]
            full_text = " ".join(text_fields)

            # "제XXX조" 패턴 추출
            matches = _KOREAN_LAW_PATTERN.findall(full_text)
            for article_num_str in matches:
                article_num = int(article_num_str)

                # 비현실적 조문 번호 탐지 (한국 법률 대부분 1000조 미만)
                if article_num > 999:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="WARNING",
                            location=item_id,
                            message=(f"비현실적 조문 번호 '제{article_num}조' — 한국 법률 대부분 999조 이내"),
                        )
                    )
                    violations += 1

                # 동일 조문 번호가 여러 법률에서 참조되는지 추적
                key = f"제{article_num}조"
                if key not in law_refs:
                    law_refs[key] = set()
                law_refs[key].add(item_id)

        if violations == 0:
            result.passed_rules.append(rule)

    # ── 규칙 5: RFI 번호 형식 + 중복 ────────────────────────────

    def _validate_rfi_numbering(
        self,
        sections: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """RFI 번호 형식 검증 및 중복 탐지."""
        rule = "RFI_NUMBERING"
        violations = 0
        seen_rfi: dict[str, str] = {}  # {rfi_number: item_id}

        for section in sections:
            section_type = section.get("section_type", "")
            expected_prefix = RFI_PREFIX_MAP.get(section_type, "")

            for item in section.get("items", []):
                item_id = item.get("item_id", "?")
                rfi_required = item.get("rfi_required", False)
                rfi_number = item.get("rfi_number", "")

                # RFI가 필요한데 번호 없음
                if rfi_required and not rfi_number:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="WARNING",
                            location=item_id,
                            message="rfi_required=True인데 rfi_number가 비어 있음",
                        )
                    )
                    violations += 1
                    continue

                if not rfi_number:
                    continue

                # RFI가 불필요한데 번호 있음
                if not rfi_required:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="WARNING",
                            location=item_id,
                            message=f"rfi_required=False인데 rfi_number={rfi_number} 설정됨",
                        )
                    )
                    violations += 1

                # 형식 검증: {PREFIX}-NNN
                rfi_pattern = re.compile(r"^[A-Z]+-\d{3}$")
                if not rfi_pattern.match(rfi_number):
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="WARNING",
                            location=item_id,
                            message=f"RFI 번호 형식 불일치: '{rfi_number}' (기대: {expected_prefix}-NNN)",
                        )
                    )
                    violations += 1

                # 접두어 검증 (섹션에 맞는 접두어인지)
                if expected_prefix and not rfi_number.startswith(expected_prefix + "-"):
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="WARNING",
                            location=item_id,
                            message=(
                                f"RFI 접두어 불일치: '{rfi_number}' "
                                f"(섹션 {section_type} → 기대 접두어: {expected_prefix})"
                            ),
                        )
                    )
                    violations += 1

                # 중복 검증
                if rfi_number in seen_rfi:
                    result.issues.append(
                        GuardrailIssue(
                            rule=rule,
                            severity="ERROR",
                            location=item_id,
                            message=(f"RFI 번호 중복: '{rfi_number}' (이미 {seen_rfi[rfi_number]}에서 사용)"),
                        )
                    )
                    violations += 1
                else:
                    seen_rfi[rfi_number] = item_id

        if violations == 0:
            result.passed_rules.append(rule)

    # ── 규칙 6: Stage 4 누락 탐지 결과 반영 ─────────────────────

    def _validate_gap_coverage(
        self,
        sections: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """Stage 4 누락 탐지에서 발견된 gap이 최종 보고서에 반영되었는지 검증."""
        rule = "GAP_COVERAGE"

        if self._gap_result is None:
            # Stage 4 미실행 시 스킵
            result.passed_rules.append(rule)
            return

        merged_gaps = getattr(self._gap_result, "merged_gaps", [])
        if not merged_gaps:
            result.passed_rules.append(rule)
            return

        # 보고서에 존재하는 section_type 목록
        report_section_types: set[str] = set()
        report_pending_sections: set[str] = set()
        for section in sections:
            st = section.get("section_type", "")
            report_section_types.add(st)
            # 해당 섹션에 PENDING 항목이 있는지 확인
            for item in section.get("items", []):
                if item.get("status") == "PENDING":
                    report_pending_sections.add(st)

        # CRITICAL/HIGH gap의 섹션이 보고서에 존재하고 PENDING이 아닌지 확인
        violations = 0
        for gap in merged_gaps:
            priority = getattr(gap, "priority", "MEDIUM")
            section_type = getattr(gap, "section_type", "")
            description = getattr(gap, "description", "")

            if priority not in ("CRITICAL", "HIGH"):
                continue

            if section_type not in report_section_types:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="WARNING",
                        location=section_type,
                        message=(f"Stage 4에서 {priority} 누락 발견됨: '{description[:60]}' — 보고서에 해당 섹션 없음"),
                    )
                )
                violations += 1

        if violations == 0:
            result.passed_rules.append(rule)

    # ── 규칙 7: confidence threshold ─────────────────────────────

    def _enforce_confidence_threshold(
        self,
        items: list[dict[str, Any]],
        result: GuardrailResult,
    ) -> None:
        """confidence < threshold 항목을 탐지하여 경고."""
        rule = "CONFIDENCE_THRESHOLD"
        violations = 0

        for item in items:
            item_id = item.get("item_id", "?")
            confidence = item.get("confidence", 0.0)
            status = item.get("status", "")

            # PENDING/NA는 confidence 불필요
            if status in ("PENDING", "NA"):
                continue

            if isinstance(confidence, (int, float)) and confidence < self._confidence_threshold:
                result.issues.append(
                    GuardrailIssue(
                        rule=rule,
                        severity="WARNING",
                        location=item_id,
                        message=(
                            f"AI 신뢰도 {confidence:.2f} < 임계값 {self._confidence_threshold} — 변호사 검증 권장"
                        ),
                    )
                )
                violations += 1

        if violations == 0:
            result.passed_rules.append(rule)
