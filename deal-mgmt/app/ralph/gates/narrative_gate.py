"""LDD 서술(Narrative) 품질 게이트.

NarrativeQualityGate 검증 항목:
1. 최소 분량 (ISSUE 항목 2000자+)
2. 법률 인용 존재 (1개 이상)
3. 6블록 중 최소 4블록 존재
4. 소스 문서 참조 존재
5. 모호한 표현 탐지 ("주의 필요" 같은 추상적 진술)
6. 거래 영향 구체성 (금액/비율/기간 포함)

LLM 없이 규칙 기반으로 밀리초 단위로 동작.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

# ── 모호한 표현 패턴 ─────────────────────────────────────────────────────

_VAGUE_PATTERNS: list[re.Pattern] = [
    re.compile(r"주의\s*(가\s*)?필요"),
    re.compile(r"검토\s*(가\s*)?필요"),
    re.compile(r"확인\s*(이\s*)?필요"),
    re.compile(r"유의\s*(가\s*)?필요"),
    re.compile(r"리스크\s*(가\s*)?있"),
    re.compile(r"문제\s*(가\s*)?될\s*수\s*있"),
    re.compile(r"가능성\s*(이\s*)?있"),
    re.compile(r"우려\s*(가\s*)?있"),
]

# ── 구체성 패턴 (금액/비율/기간) ──────────────────────────────────────────

_SPECIFICITY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d+[,.]?\d*\s*(억|만|천|백)\s*원"),  # 금액
    re.compile(r"\d+[.]?\d*\s*%"),  # 비율
    re.compile(r"\d+\s*(년|개월|일|주|개월간|년간)"),  # 기간
    re.compile(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}"),  # 날짜
    re.compile(r"\d+\s*(건|개|명|호|세대)"),  # 수량
]

# ── 법률 인용 패턴 ─────────────────────────────────────────────────────

_CITATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\[cite:[^\]]+\]"),  # [cite:ID] 태그
    re.compile(r"[\w가-힣]+법\s+제\d+조"),  # 법조문
    re.compile(r"대법원.*?\d{4}[다두]\w+"),  # 판례
]


@dataclass
class NarrativeItemQuality:
    """단일 항목의 서술 품질 평가 결과."""

    item_id: str
    item_name: str
    status: str  # ISSUE / OK / NA / PENDING
    issue_level: str | None = None

    # 측정값
    total_chars: int = 0
    block_count: int = 0
    citation_count: int = 0
    vague_expressions: list[str] = field(default_factory=list)
    specificity_count: int = 0
    has_source_ref: bool = False

    # 판정
    issues: list[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "status": self.status,
            "issue_level": self.issue_level,
            "total_chars": self.total_chars,
            "block_count": self.block_count,
            "citation_count": self.citation_count,
            "vague_count": len(self.vague_expressions),
            "specificity_count": self.specificity_count,
            "has_source_ref": self.has_source_ref,
            "issues": self.issues,
            "passed": self.passed,
        }


@dataclass
class NarrativeQualityResult:
    """전체 서술 품질 평가 결과."""

    total_items: int = 0
    passed_items: int = 0
    failed_items: int = 0
    items: list[NarrativeItemQuality] = field(default_factory=list)
    summary_issues: list[str] = field(default_factory=list)
    overall_score: float = 0.0  # 0.0 ~ 5.0
    duration_ms: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total_items == 0:
            return 1.0
        return self.passed_items / self.total_items

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "passed_items": self.passed_items,
            "failed_items": self.failed_items,
            "pass_rate": round(self.pass_rate, 3),
            "overall_score": round(self.overall_score, 2),
            "duration_ms": self.duration_ms,
            "summary_issues": self.summary_issues,
            "items": [i.to_dict() for i in self.items],
        }


class NarrativeQualityGate:
    """LDD 서술 품질 게이트 (규칙 기반).

    LLM 호출 없이 밀리초 단위로 동작한다.
    """

    def __init__(
        self,
        *,
        min_chars_critical: int = 2000,
        min_chars_high: int = 1500,
        min_chars_medium: int = 800,
        min_blocks_issue: int = 4,
        min_citations_issue: int = 1,
        max_vague_expressions: int = 2,
    ) -> None:
        self._min_chars = {
            "CRITICAL": min_chars_critical,
            "HIGH": min_chars_high,
            "MEDIUM": min_chars_medium,
            "LOW": 400,
        }
        self._min_blocks_issue = min_blocks_issue
        self._min_citations_issue = min_citations_issue
        self._max_vague = max_vague_expressions

    def evaluate(
        self,
        narrative_sections: dict[str, list[dict[str, Any]]],
    ) -> NarrativeQualityResult:
        """전체 narrative_sections를 평가한다."""
        start = time.perf_counter_ns()
        items: list[NarrativeItemQuality] = []
        summary_issues: list[str] = []

        for section_type, section_items in narrative_sections.items():
            for item_data in section_items:
                quality = self._evaluate_item(item_data, section_type)
                items.append(quality)

        total = len(items)
        passed = sum(1 for i in items if i.passed)
        failed = total - passed

        if failed > 0:
            summary_issues.append(f"{failed}개 항목이 품질 기준 미달")

        # 전체 점수 (5.0 만점)
        score = passed / total * 5.0 if total > 0 else 5.0

        elapsed_ms = int((time.perf_counter_ns() - start) / 1_000_000)

        return NarrativeQualityResult(
            total_items=total,
            passed_items=passed,
            failed_items=failed,
            items=items,
            summary_issues=summary_issues,
            overall_score=score,
            duration_ms=elapsed_ms,
        )

    def _evaluate_item(
        self,
        item_data: dict,
        section_type: str,
    ) -> NarrativeItemQuality:
        """단일 항목 서술을 평가한다."""
        item_id = item_data.get("item_id", "")
        item_name = item_data.get("item_name", "")
        blocks = item_data.get("blocks", [])
        status = "ISSUE" if blocks else "OK"
        issue_level = None

        # 전체 텍스트 합산
        all_text = " ".join(b.get("content", "") for b in blocks)
        total_chars = len(all_text)
        block_count = len(blocks)

        # issue_level 추측 (blocks 수로)
        if block_count >= 5:
            issue_level = "CRITICAL"
            status = "ISSUE"
        elif block_count >= 4:
            issue_level = "HIGH"
            status = "ISSUE"
        elif block_count >= 2:
            issue_level = "MEDIUM"
            status = "ISSUE"
        elif block_count == 1:
            status = "OK"

        quality = NarrativeItemQuality(
            item_id=item_id,
            item_name=item_name,
            status=status,
            issue_level=issue_level,
            total_chars=total_chars,
            block_count=block_count,
        )

        if block_count == 0:
            return quality

        # 1. 최소 분량 검사
        if issue_level and status == "ISSUE":
            min_chars = self._min_chars.get(issue_level, 400)
            if total_chars < min_chars:
                quality.issues.append(f"분량 미달: {total_chars}자 < {min_chars}자 (최소 기준)")

        # 2. 법률 인용 검사
        citation_count = sum(len(p.findall(all_text)) for p in _CITATION_PATTERNS)
        quality.citation_count = citation_count
        if status == "ISSUE" and citation_count < self._min_citations_issue:
            quality.issues.append("법률 인용 없음 (ISSUE 항목은 최소 1개 인용 필요)")

        # 3. 블록 수 검사
        if status == "ISSUE" and block_count < self._min_blocks_issue:
            quality.issues.append(f"블록 수 부족: {block_count}개 < {self._min_blocks_issue}개 (최소 기준)")

        # 4. 소스 문서 참조 검사
        source_refs = bool(re.search(r"(자료|문서|계약서|보고서|감사보고서|등기부|확인서)", all_text))
        quality.has_source_ref = source_refs
        if status == "ISSUE" and not source_refs:
            quality.issues.append("소스 문서 참조 없음")

        # 5. 모호한 표현 탐지
        vague_found: list[str] = []
        for pattern in _VAGUE_PATTERNS:
            matches = pattern.findall(all_text)
            vague_found.extend(matches)
        quality.vague_expressions = vague_found
        if len(vague_found) > self._max_vague:
            quality.issues.append(f"모호한 표현 과다: {len(vague_found)}개 (허용: {self._max_vague}개)")

        # 6. 구체성 검사 (DEAL_IMPACT 블록)
        deal_impact_text = ""
        for b in blocks:
            if b.get("block_type") == "DEAL_IMPACT":
                deal_impact_text = b.get("content", "")
                break

        if deal_impact_text:
            specificity = sum(len(p.findall(deal_impact_text)) for p in _SPECIFICITY_PATTERNS)
            quality.specificity_count = specificity
            if specificity == 0:
                quality.issues.append("거래 영향 블록에 구체적 수치(금액/비율/기간) 없음")

        # 판정
        quality.passed = len(quality.issues) == 0
        return quality
