"""Stage 4: 누락 탐지 — 멀티 LLM 합집합 (최대 ROI 구간).

체크리스트 기반 + 자유 탐색 기반 = 합집합으로
단일 모델 대비 커버리지 극대화.

핵심:
- LLM A (체크리스트 기반): "M&A 표준 LDD 체크리스트 대비 누락 항목"
- LLM B (자유 탐색 기반): "거래 특수성 고려 추가 확인 사항"
- 합집합 = 최종 누락 목록 (중복 제거, 우선순위 정렬)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from app.ralph.generators.ldd.json_utils import extract_json
from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig

logger = logging.getLogger(__name__)


# ── 데이터 클래스 ──────────────────────────────────────────────────

@dataclass
class GapItem:
    """단일 누락 항목."""

    gap_id: str
    section_type: str
    description: str
    priority: str  # CRITICAL | HIGH | MEDIUM | LOW
    rationale: str
    source: str  # "checklist" | "freeform"
    is_duplicate: bool = False
    merged_with: str | None = None  # 중복 시 병합 대상 gap_id


@dataclass
class GapDetectionResult:
    """누락 탐지 전체 결과."""

    checklist_gaps: list[GapItem] = field(default_factory=list)
    freeform_gaps: list[GapItem] = field(default_factory=list)
    merged_gaps: list[GapItem] = field(default_factory=list)
    total_checklist: int = 0
    total_freeform: int = 0
    total_unique: int = 0
    duplicates_removed: int = 0


# ── 프롬프트 ──────────────────────────────────────────────────────

CHECKLIST_GAP_SYSTEM = """\
당신은 M&A 법률실사(LDD) 품질 관리 전문가입니다.
표준 DDRL 체크리스트를 기준으로 누락된 검토 항목을 식별합니다.
"""

CHECKLIST_GAP_PROMPT = """\
## 현재까지 분석 완료된 항목

{analyzed_items_summary}

## 거래 정보

- 거래 유형: {deal_type}
- 대상 산업: {industry}

## 지침

M&A 법률실사 표준 체크리스트(DDRL 기재례) 대비 **누락된 검토 항목**을 찾으세요.

고려 섹션: GOVERNANCE, CAPITAL, CONTRACTS, LITIGATION, LABOR, IP, REAL_ESTATE, PERMITS, TAX, DATA_IT

JSON 배열로 반환하세요:
```json
[
  {{
    "gap_id": "GAP-001",
    "section_type": "CONTRACTS",
    "description": "Change of Control 조항 검토 누락",
    "priority": "CRITICAL",
    "rationale": "주요 계약의 CoC 조항 미확인 시 거래 후 계약 해지 위험"
  }}
]
```

누락 항목이 없으면 빈 배열 `[]`을 반환하세요.
JSON만 반환하고 다른 텍스트는 포함하지 마세요.
"""

FREEFORM_GAP_SYSTEM = """\
당신은 M&A 거래 전문 시니어 변호사입니다.
표준 체크리스트를 넘어서, 거래의 특수성을 고려한 추가 검토 사항을 탐색합니다.
"""

FREEFORM_GAP_PROMPT = """\
## 거래 요약

{deal_summary}

## 대상 산업

{industry}

## 분석된 문서 목록

{document_list}

## 지침

이 거래의 **특수성**을 고려하여, 표준 체크리스트에는 없지만
추가로 확인해야 할 법률 리스크를 탐색하세요.

고려 사항:
- 해당 산업의 특수 규제 (예: 식품→식약처 인허가, 금융→금감원 인가)
- 최근 법률/규정 개정의 영향
- 거래 구조의 특이점 (예: 합작법인, 사업양수도)
- 대상회사의 사업 특성에서 비롯되는 리스크

JSON 배열로 반환하세요:
```json
[
  {{
    "gap_id": "FGAP-001",
    "section_type": "PERMITS",
    "description": "식약처 인허가 이전 가능 여부 검토 필요",
    "priority": "HIGH",
    "rationale": "대상회사가 식품 제조업으로 식약처 인허가가 필수이며, M&A 시 이전 절차 확인 필요"
  }}
]
```

추가 검토 사항이 없으면 빈 배열 `[]`을 반환하세요.
JSON만 반환하고 다른 텍스트는 포함하지 마세요.
"""


# ── 메인 클래스 ──────────────────────────────────────────────────

class GapDetector:
    """Stage 4: 누락 탐지 — 멀티 LLM 합집합."""

    def __init__(
        self,
        llm_client,
        router=None,
        config: LDDPipelineConfig | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._router = router
        self._config = config or LDDPipelineConfig()

    async def detect_gaps(
        self,
        analyzed_sections: dict[str, list[dict]],
        document_names: list[str],
    ) -> GapDetectionResult:
        """누락 항목을 탐지한다.

        Args:
            analyzed_sections: {section_type: [item_dict, ...]}
            document_names: 분석된 VDR 문서명 목록
        """
        # 분석 완료 항목 요약 생성
        items_summary = self._build_items_summary(analyzed_sections)
        doc_list = "\n".join(f"- {name}" for name in document_names[:30])

        # 병렬 실행
        checklist_text, freeform_text = await asyncio.gather(
            self._call_checklist(items_summary),
            self._call_freeform(doc_list),
        )

        checklist_gaps = self._parse_gaps(checklist_text, "checklist", "GAP")
        freeform_gaps = self._parse_gaps(freeform_text, "freeform", "FGAP")

        # 합집합 (중복 제거)
        merged, duplicates = self._merge_and_deduplicate(checklist_gaps, freeform_gaps)

        return GapDetectionResult(
            checklist_gaps=checklist_gaps,
            freeform_gaps=freeform_gaps,
            merged_gaps=merged,
            total_checklist=len(checklist_gaps),
            total_freeform=len(freeform_gaps),
            total_unique=len(merged),
            duplicates_removed=duplicates,
        )

    # ── Private Methods ──────────────────────────────────────────

    async def _call_checklist(self, items_summary: str) -> str:
        prompt = CHECKLIST_GAP_PROMPT.format(
            analyzed_items_summary=items_summary,
            deal_type=self._config.deal_type or "M&A",
            industry=self._config.industry or "일반",
        )
        if self._router:
            return await self._router.call_routed("gap_detection_checklist", CHECKLIST_GAP_SYSTEM, prompt)
        return await self._llm_client.call(CHECKLIST_GAP_SYSTEM, prompt)

    async def _call_freeform(self, doc_list: str) -> str:
        prompt = FREEFORM_GAP_PROMPT.format(
            deal_summary=self._config.deal_summary or "(거래 요약 미제공)",
            industry=self._config.industry or "일반",
            document_list=doc_list or "(문서 없음)",
        )
        if self._router:
            return await self._router.call_routed("gap_detection_freeform", FREEFORM_GAP_SYSTEM, prompt)
        return await self._llm_client.call(FREEFORM_GAP_SYSTEM, prompt)

    def _build_items_summary(self, sections: dict[str, list[dict]]) -> str:
        parts: list[str] = []
        for section_type, items in sections.items():
            ok = sum(1 for i in items if i.get("status") == "OK")
            issue = sum(1 for i in items if i.get("status") == "ISSUE")
            na = sum(1 for i in items if i.get("status") == "NA")
            pending = sum(1 for i in items if i.get("status") == "PENDING")
            parts.append(
                f"- {section_type}: 총 {len(items)}개 "
                f"(OK={ok}, ISSUE={issue}, NA={na}, PENDING={pending})"
            )
            for item in items:
                if item.get("status") == "ISSUE":
                    parts.append(
                        f"  - [{item.get('issue_level', '?')}] "
                        f"{item.get('item_id', '')}: {item.get('description', '')[:80]}"
                    )
        return "\n".join(parts)

    def _parse_gaps(self, raw: str, source: str, prefix: str) -> list[GapItem]:
        items = extract_json(raw, context=f"누락 탐지 source={source}", fallback=[])
        if not isinstance(items, list):
            return []

        gaps: list[GapItem] = []
        for i, item in enumerate(items):
            gaps.append(GapItem(
                gap_id=item.get("gap_id", f"{prefix}-{i+1:03d}"),
                section_type=item.get("section_type", "UNKNOWN"),
                description=item.get("description", ""),
                priority=item.get("priority", "MEDIUM"),
                rationale=item.get("rationale", ""),
                source=source,
            ))
        return gaps

    def _merge_and_deduplicate(
        self,
        checklist: list[GapItem],
        freeform: list[GapItem],
    ) -> tuple[list[GapItem], int]:
        """합집합을 생성하고 중복을 제거한다."""
        all_gaps = checklist + freeform
        if not all_gaps:
            return [], 0

        threshold = self._config.gap_similarity_threshold
        merged: list[GapItem] = []
        duplicates = 0

        for gap in all_gaps:
            is_dup = False
            for existing in merged:
                similarity = self._jaccard_similarity(
                    gap.description + " " + gap.section_type,
                    existing.description + " " + existing.section_type,
                )
                if similarity > threshold:
                    is_dup = True
                    duplicates += 1
                    gap.is_duplicate = True
                    gap.merged_with = existing.gap_id
                    # 우선순위가 높으면 교체
                    priority_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
                    if priority_map.get(gap.priority, 0) > priority_map.get(existing.priority, 0):
                        existing.priority = gap.priority
                    # 근거 병합
                    if gap.rationale and gap.rationale not in existing.rationale:
                        existing.rationale += f"\n[추가 근거] {gap.rationale}"
                    break

            if not is_dup:
                merged.append(gap)

        # 우선순위별 정렬 (CRITICAL → LOW)
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        merged.sort(key=lambda g: priority_order.get(g.priority, 9))

        return merged, duplicates

    @staticmethod
    def _jaccard_similarity(text_a: str, text_b: str) -> float:
        """두 텍스트의 Jaccard 유사도를 계산한다."""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0
