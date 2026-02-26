"""Stage 3: 듀얼 관점 리스크 분석 — 멀티 LLM 핵심 모듈.

동일 조항/항목을 2개 LLM이 서로 다른 관점으로 병렬 분석하고,
deterministic gap 비교로 불일치를 탐지한다.

설계 원칙:
- LLM A (매수인 관점) + LLM B (독립 리스크 평가) 병렬 실행
- gap=0: 자동 확정
- gap=1: 높은 쪽 채택 + 양측 근거 병기
- gap≥2: 변호사 필수 검토
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.ralph.generators.ldd.json_utils import extract_json
from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig
from app.ralph.generators.ldd.prompts import format_source_materials
from app.ralph.parsers.base import ParsedFile

logger = logging.getLogger(__name__)

# ── 리스크 등급 수치화 ──────────────────────────────────────────────

DEFAULT_LEVEL_MAP: dict[str, int] = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ── 데이터 클래스 ──────────────────────────────────────────────────

@dataclass
class PerspectiveResult:
    """단일 관점 분석 결과."""

    perspective: str  # "buyer" or "independent"
    item_id: str
    status: str
    issue_level: str | None
    description: str
    deal_impact: str
    recommendation: str
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskComparison:
    """듀얼 분석 비교 결과."""

    item_id: str
    gap: int  # 등급 차이 (0, 1, 2, 3)
    final_level: str | None  # 최종 확정 등급 (자동 해결 시)
    auto_resolved: bool
    needs_human_review: bool = False
    note: str = ""
    buyer_rationale: str = ""
    independent_rationale: str = ""


@dataclass
class DualAnalysisResult:
    """항목별 듀얼 분석 전체 결과."""

    item_id: str
    buyer: PerspectiveResult
    independent: PerspectiveResult
    comparison: RiskComparison
    # 병합된 최종 결과 (서비스 레이어에서 사용)
    merged: dict[str, Any] = field(default_factory=dict)


# ── 프롬프트 ──────────────────────────────────────────────────────

BUYER_PERSPECTIVE_SYSTEM = """\
당신은 매수인측 법률 자문 변호사입니다.
대형 로펌(김앤장, 세종, 태평양, 광장)급 법률실사 전문가로서,
매수인 입장에서 리스크를 평가합니다.

핵심 관점:
1. 거래 완결(Closing)에 미치는 영향
2. 인수 후 사업 영위에 미치는 위험
3. 가격 조정 또는 진술보장(R&W) 요구 필요성
4. 면책(Indemnity) 조항 필요 여부

Issue Level 판정:
- CRITICAL: 거래 중단 또는 근본적 재구조화 필요
- HIGH: 가격 조정 또는 계약 조건 변경 필요
- MEDIUM: 진술보장/면책 반영 필요
- LOW: 모니터링 수준

JSON만 반환하세요.
"""

INDEPENDENT_RISK_SYSTEM = """\
당신은 독립적인 법률실사 전문가입니다.
편향 없이 객관적으로 리스크를 평가합니다.

핵심 관점:
1. 편향 없는 객관적 리스크 등급 판정
2. 최악의 시나리오(worst-case) 분석 포함
3. 유사 거래 선례/판례 기반 근거 제시
4. 이해관계 없는 제3자 관점

동일한 Issue Level 기준을 적용하되,
매수인/매도인 어느 쪽에도 치우치지 않습니다.

JSON만 반환하세요.
"""


# ── 메인 클래스 ──────────────────────────────────────────────────

class DualRiskAnalyzer:
    """Stage 3: 듀얼 관점 리스크 분석.

    동일 DDRL 항목을 2개 LLM이 병렬 분석하고,
    결과를 deterministic gap 비교로 통합한다.
    """

    def __init__(
        self,
        llm_client,
        router=None,
        config: LDDPipelineConfig | None = None,
        learned_patterns: list[str] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._router = router
        self._config = config or LDDPipelineConfig()
        self._learned_patterns = learned_patterns or []

    async def analyze_item_dual(
        self,
        item_id: str,
        item_name: str,
        section_type: str,
        section_title: str,
        source_files: list[ParsedFile],
        feedback: str = "",
    ) -> DualAnalysisResult:
        """단일 항목을 듀얼 관점으로 분석한다."""
        materials = format_source_materials([
            {
                "name": f.source_path.split("/")[-1].split("\\")[-1],
                "text": f.text,
                "tables": [{"headers": t.headers, "rows": t.rows[:3]} for t in f.tables[:3]],
            }
            for f in source_files if f.is_valid
        ])

        user_prompt = self._build_user_prompt(
            item_id, item_name, section_type, section_title, materials, feedback,
        )

        # 병렬 실행: 매수인 관점 + 독립 평가
        buyer_text, independent_text = await asyncio.gather(
            self._call_perspective("risk_analysis_buyer", BUYER_PERSPECTIVE_SYSTEM, user_prompt),
            self._call_perspective("risk_analysis_independent", INDEPENDENT_RISK_SYSTEM, user_prompt),
        )

        buyer = self._parse_result(buyer_text, "buyer", item_id)
        independent = self._parse_result(independent_text, "independent", item_id)

        # Deterministic gap 비교
        comparison = self._compare_risk_levels(item_id, buyer, independent)

        # 병합 결과 생성
        merged = self._build_merged_result(buyer, independent, comparison)

        return DualAnalysisResult(
            item_id=item_id,
            buyer=buyer,
            independent=independent,
            comparison=comparison,
            merged=merged,
        )

    async def analyze_all(
        self,
        sections_config: list[dict],
        source_map: dict[str, list[ParsedFile]],
    ) -> dict[str, list[DualAnalysisResult]]:
        """모든 섹션의 모든 항목을 듀얼 분석한다."""
        results: dict[str, list[DualAnalysisResult]] = {}

        for sec in sections_config:
            section_type = sec["section_type"]
            section_title = sec["title"]
            source_files = source_map.get(section_type, [])
            section_results: list[DualAnalysisResult] = []

            for item in sec["items"]:
                result = await self.analyze_item_dual(
                    item_id=item["item_id"],
                    item_name=item["name"],
                    section_type=section_type,
                    section_title=section_title,
                    source_files=source_files,
                )
                section_results.append(result)

            results[section_type] = section_results

        return results

    # ── Private Methods ──────────────────────────────────────────

    async def _call_perspective(
        self, routing_key: str, system: str, user: str,
    ) -> str:
        """라우터로 특정 관점의 LLM을 호출한다."""
        # 학습 패턴 주입
        enriched_system = system
        if self._learned_patterns:
            from app.ralph.learning.prompt_injector import LearningPromptInjector
            enriched_system = LearningPromptInjector().enrich_system_prompt(
                system, self._learned_patterns,
            )

        if self._router:
            return await self._router.call_routed(routing_key, enriched_system, user)
        return await self._llm_client.call(enriched_system, user)

    def _build_user_prompt(
        self,
        item_id: str,
        item_name: str,
        section_type: str,
        section_title: str,
        materials: str,
        feedback: str,
    ) -> str:
        feedback_section = f"## 이전 피드백\n{feedback}" if feedback else ""
        return f"""\
## 분석 대상

**항목**: {item_id} — {item_name}
**섹션**: {section_type} ({section_title})

## 제공된 실사자료

{materials}

{feedback_section}

## 응답 형식

```json
{{
  "status": "OK | ISSUE | NA | PENDING",
  "issue_level": "CRITICAL | HIGH | MEDIUM | LOW | null",
  "description": "사실관계 서술",
  "deal_impact": "거래에 미치는 영향",
  "recommendation": "권고사항",
  "confidence": 0.0-1.0,
  "evidence_refs": ["파일명1"]
}}
```

JSON만 반환하세요.
"""

    def _parse_result(
        self, raw_text: str, perspective: str, item_id: str,
    ) -> PerspectiveResult:
        """LLM 응답을 PerspectiveResult로 파싱한다."""
        data = extract_json(
            raw_text,
            context=f"듀얼 분석 perspective={perspective}, item={item_id}",
            fallback={
                "status": "PENDING",
                "issue_level": None,
                "description": "분석 결과 파싱 실패",
                "deal_impact": "",
                "recommendation": "",
                "confidence": 0.0,
                "evidence_refs": [],
            },
        )

        return PerspectiveResult(
            perspective=perspective,
            item_id=item_id,
            status=data.get("status", "PENDING"),
            issue_level=data.get("issue_level"),
            description=data.get("description", ""),
            deal_impact=data.get("deal_impact", ""),
            recommendation=data.get("recommendation", ""),
            confidence=float(data.get("confidence", 0.0)),
            evidence_refs=data.get("evidence_refs", []),
            raw=data,
        )

    def _compare_risk_levels(
        self,
        item_id: str,
        buyer: PerspectiveResult,
        independent: PerspectiveResult,
    ) -> RiskComparison:
        """두 관점의 리스크 등급을 비교한다."""
        level_map = self._config.level_map

        # 상태 불일치 처리: 한쪽만 ISSUE인 경우
        b_is_issue = buyer.status == "ISSUE"
        i_is_issue = independent.status == "ISSUE"

        if b_is_issue != i_is_issue:
            # 한쪽만 ISSUE → gap=2 (변호사 검토)
            return RiskComparison(
                item_id=item_id,
                gap=2,
                final_level=None,
                auto_resolved=False,
                needs_human_review=True,
                note=(
                    f"상태 불일치: Buyer={buyer.status}({buyer.issue_level}), "
                    f"Independent={independent.status}({independent.issue_level})"
                ),
                buyer_rationale=buyer.description,
                independent_rationale=independent.description,
            )

        # 둘 다 ISSUE가 아닌 경우 → 일치
        if not b_is_issue and not i_is_issue:
            return RiskComparison(
                item_id=item_id,
                gap=0,
                final_level=None,
                auto_resolved=True,
                note=f"양측 일치: Buyer={buyer.status}, Independent={independent.status}",
            )

        # 둘 다 ISSUE → 등급 비교
        b_level = level_map.get(buyer.issue_level or "", 0)
        i_level = level_map.get(independent.issue_level or "", 0)
        gap = abs(b_level - i_level)

        if gap == 0:
            return RiskComparison(
                item_id=item_id,
                gap=0,
                final_level=buyer.issue_level,
                auto_resolved=True,
                note=f"등급 일치: {buyer.issue_level}",
            )
        elif gap <= self._config.risk_gap_auto_resolve:
            # 높은 쪽 채택 + 양측 근거 병기
            higher = buyer if b_level > i_level else independent
            return RiskComparison(
                item_id=item_id,
                gap=gap,
                final_level=higher.issue_level,
                auto_resolved=True,
                note=(
                    f"자동 해결 (gap={gap}): "
                    f"Buyer={buyer.issue_level}, Independent={independent.issue_level} "
                    f"→ {higher.issue_level} 채택"
                ),
                buyer_rationale=buyer.description,
                independent_rationale=independent.description,
            )
        else:
            return RiskComparison(
                item_id=item_id,
                gap=gap,
                final_level=None,
                auto_resolved=False,
                needs_human_review=True,
                note=(
                    f"변호사 검토 필요 (gap={gap}): "
                    f"Buyer={buyer.issue_level}, Independent={independent.issue_level}"
                ),
                buyer_rationale=buyer.description,
                independent_rationale=independent.description,
            )

    def _build_merged_result(
        self,
        buyer: PerspectiveResult,
        independent: PerspectiveResult,
        comparison: RiskComparison,
    ) -> dict[str, Any]:
        """듀얼 분석 결과를 병합하여 기존 LDDItem 형식으로 변환한다."""
        if comparison.auto_resolved:
            # 자동 해결 → 확정된 결과 사용
            if comparison.final_level:
                # 둘 다 ISSUE → 확정 등급
                primary = buyer if buyer.issue_level == comparison.final_level else independent
                return {
                    "item_id": buyer.item_id,
                    "status": "ISSUE",
                    "issue_level": comparison.final_level,
                    "description": primary.description,
                    "deal_impact": primary.deal_impact,
                    "recommendation": primary.recommendation,
                    "confidence": max(buyer.confidence, independent.confidence),
                    "evidence_refs": list(set(buyer.evidence_refs + independent.evidence_refs)),
                    "dual_analysis": {
                        "buyer_level": buyer.issue_level,
                        "independent_level": independent.issue_level,
                        "gap": comparison.gap,
                        "resolution": comparison.note,
                        "buyer_rationale": comparison.buyer_rationale,
                        "independent_rationale": comparison.independent_rationale,
                    },
                }
            else:
                # 둘 다 non-ISSUE
                return {
                    "item_id": buyer.item_id,
                    "status": buyer.status,
                    "issue_level": None,
                    "description": buyer.description or independent.description,
                    "deal_impact": buyer.deal_impact or independent.deal_impact,
                    "recommendation": buyer.recommendation or independent.recommendation,
                    "confidence": max(buyer.confidence, independent.confidence),
                    "evidence_refs": list(set(buyer.evidence_refs + independent.evidence_refs)),
                }
        else:
            # 미해결 → FLAGGED로 마킹, 양측 근거 모두 보존
            higher = buyer if (DEFAULT_LEVEL_MAP.get(buyer.issue_level or "", 0)
                              >= DEFAULT_LEVEL_MAP.get(independent.issue_level or "", 0)) else independent
            return {
                "item_id": buyer.item_id,
                "status": "ISSUE",
                "issue_level": higher.issue_level or buyer.issue_level or independent.issue_level,
                "description": (
                    f"[변호사 검토 필요] 리스크 판단 불일치 (gap={comparison.gap})\n\n"
                    f"--- 매수인 관점 ({buyer.issue_level}) ---\n{buyer.description}\n\n"
                    f"--- 독립 평가 ({independent.issue_level}) ---\n{independent.description}"
                ),
                "deal_impact": (
                    f"매수인 관점: {buyer.deal_impact}\n"
                    f"독립 평가: {independent.deal_impact}"
                ),
                "recommendation": (
                    f"매수인 관점: {buyer.recommendation}\n"
                    f"독립 평가: {independent.recommendation}"
                ),
                "confidence": min(buyer.confidence, independent.confidence),
                "evidence_refs": list(set(buyer.evidence_refs + independent.evidence_refs)),
                "dual_analysis": {
                    "buyer_level": buyer.issue_level,
                    "independent_level": independent.issue_level,
                    "gap": comparison.gap,
                    "needs_human_review": True,
                    "buyer_rationale": buyer.description,
                    "independent_rationale": independent.description,
                },
            }
