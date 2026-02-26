"""6블록 서술(Narrative) → 법무법인 3단 구조 변환 어댑터.

기존 NarrativeGenerator의 6블록 체인 결과를 법무법인 양식의 3단 서술로 변환:

    6블록                         → 법무법인 3단
    ─────────────────────────────────────────────
    FACTS                         → 1. 현황
    LEGAL_REVIEW + ANALYSIS       → 2. 검토 및 분석
    + DEAL_IMPACT + PENALTY
    RECOMMENDATION                → 3. Recommendation (녹색 박스)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LawFirmNarrative:
    """법무법인 3단 서술 단일 항목."""

    item_id: str = ""
    item_name: str = ""
    chapter_number: str = ""

    status_section: str = ""       # 1. 현황
    review_section: str = ""       # 2. 검토 및 분석
    recommendation_section: str = ""  # 3. Recommendation

    irl_items: list[str] = field(default_factory=list)
    cited_laws: list[str] = field(default_factory=list)
    cited_documents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "chapter_number": self.chapter_number,
            "status_section": self.status_section,
            "review_section": self.review_section,
            "recommendation_section": self.recommendation_section,
            "irl_items": self.irl_items,
            "cited_laws": self.cited_laws,
            "cited_documents": self.cited_documents,
        }


# 6블록 타입 → 3단 매핑
_BLOCK_TO_SECTION = {
    "FACTS": "status",
    "LEGAL_REVIEW": "review",
    "ANALYSIS": "review",
    "DEAL_IMPACT": "review",
    "PENALTY": "review",
    "RECOMMENDATION": "recommendation",
}


class LawFirmNarrativeAdapter:
    """6블록 서술을 법무법인 3단 구조로 변환.

    사용법:
        adapter = LawFirmNarrativeAdapter()
        narratives = adapter.convert(narrative_results, chapters)
    """

    def convert_item(
        self,
        narrative_dict: dict[str, Any],
        chapter_number: str = "",
    ) -> LawFirmNarrative:
        """단일 항목의 6블록 서술을 3단으로 변환.

        Args:
            narrative_dict: NarrativeResult.to_dict() 결과
            chapter_number: 법무법인 목차 번호 (예: "I", "II")

        Returns:
            LawFirmNarrative
        """
        result = LawFirmNarrative(
            item_id=narrative_dict.get("item_id", ""),
            item_name=narrative_dict.get("item_name", ""),
            chapter_number=chapter_number,
        )

        blocks = narrative_dict.get("blocks", [])
        status_parts: list[str] = []
        review_parts: list[str] = []
        recommendation_parts: list[str] = []

        for block in blocks:
            block_type = block.get("block_type", "")
            content = block.get("content", "").strip()
            if not content:
                continue

            section = _BLOCK_TO_SECTION.get(block_type, "review")
            if section == "status":
                status_parts.append(content)
            elif section == "review":
                review_parts.append(content)
            elif section == "recommendation":
                recommendation_parts.append(content)

        result.status_section = "\n\n".join(status_parts) if status_parts else ""
        result.review_section = "\n\n".join(review_parts) if review_parts else ""
        result.recommendation_section = "\n\n".join(recommendation_parts) if recommendation_parts else ""

        # 6블록 텍스트에서 (D) 라벨 + IRL 항목 추출
        all_text = "\n".join(status_parts + review_parts + recommendation_parts)
        result.irl_items = _extract_irl_from_text(all_text)

        # 법률 인용 추출 (예: "상법 제374조")
        result.cited_laws = _extract_cited_laws(all_text)

        # 출처 문서 추출 (예: "(출처: 정관.pdf, 제5조)")
        result.cited_documents = _extract_cited_documents(all_text)

        return result

    def convert_chapter(
        self,
        narrative_list: list[dict[str, Any]],
        chapter_number: str = "",
    ) -> list[LawFirmNarrative]:
        """한 챕터에 속한 모든 항목의 서술을 변환."""
        return [
            self.convert_item(n, chapter_number)
            for n in narrative_list
        ]

    def convert_from_llm_response(
        self,
        llm_response: dict[str, Any],
        item_id: str = "",
        item_name: str = "",
        chapter_number: str = "",
    ) -> LawFirmNarrative:
        """LLM이 직접 3단 구조로 생성한 응답을 LawFirmNarrative로 변환.

        law_firm_prompts.LAW_FIRM_NARRATIVE_PROMPT로 생성된 응답 파싱용.
        """
        return LawFirmNarrative(
            item_id=item_id,
            item_name=item_name,
            chapter_number=chapter_number,
            status_section=llm_response.get("status_section", ""),
            review_section=llm_response.get("review_section", ""),
            recommendation_section=llm_response.get("recommendation_section", ""),
            irl_items=llm_response.get("irl_items", []),
            cited_laws=llm_response.get("cited_laws", []),
            cited_documents=llm_response.get("cited_documents", []),
        )

    def build_law_firm_sections(
        self,
        narratives_by_chapter: dict[str, list[LawFirmNarrative]],
    ) -> dict[str, Any]:
        """전체 챕터별 3단 서술을 JSONB 저장용으로 직렬화.

        LDDReport.law_firm_sections에 저장.
        """
        return {
            chapter_num: [n.to_dict() for n in narrs]
            for chapter_num, narrs in narratives_by_chapter.items()
        }

    def collect_irl_items(
        self,
        narratives_by_chapter: dict[str, list[LawFirmNarrative]],
    ) -> list[dict[str, str]]:
        """전체 D 라벨 IRL 항목을 수집.

        LDDReport.irl_items에 저장.
        """
        irl_list: list[dict[str, str]] = []
        for chapter_num, narrs in narratives_by_chapter.items():
            for narr in narrs:
                for irl in narr.irl_items:
                    irl_list.append({
                        "chapter": chapter_num,
                        "item_id": narr.item_id,
                        "item_name": narr.item_name,
                        "request": irl,
                    })
        return irl_list


# ── 텍스트 기반 메타데이터 추출 유틸리티 ────────────────────────────────────

# (D) 라벨 뒤 IRL 패턴: "(D) → IRL: 환경영향평가서 사본 요청" 또는 "(D)"만 있는 경우
_IRL_PATTERN = re.compile(
    r"\(D\)\s*(?:→\s*IRL\s*[:：]\s*(.+?)(?:\n|$))",
    re.MULTILINE,
)

# 법률 인용 패턴: "[법률명] 제[N]조" (예: 상법 제374조, 독점규제법 제7조)
_LAW_CITE_PATTERN = re.compile(
    r"([\w가-힣]+법(?:\s*시행[령규칙]+)?)\s+제\s*(\d+)\s*조",
)

# 출처 문서 패턴: "(출처: 문서명, 조항/페이지)"
_DOC_CITE_PATTERN = re.compile(
    r"\(출처\s*[:：]\s*(.+?)\)",
)


def _extract_irl_from_text(text: str) -> list[str]:
    """(D) 라벨이 포함된 문장에서 IRL 요청 항목을 추출."""
    if not text:
        return []
    results: list[str] = []
    for match in _IRL_PATTERN.finditer(text):
        irl_text = match.group(1).strip()
        if irl_text and irl_text not in results:
            results.append(irl_text)
    return results


def _extract_cited_laws(text: str) -> list[str]:
    """텍스트에서 법률 인용을 추출."""
    if not text:
        return []
    results: list[str] = []
    for match in _LAW_CITE_PATTERN.finditer(text):
        citation = f"{match.group(1)} 제{match.group(2)}조"
        if citation not in results:
            results.append(citation)
    return results


def _extract_cited_documents(text: str) -> list[str]:
    """텍스트에서 "(출처: ...)" 패턴의 문서를 추출."""
    if not text:
        return []
    results: list[str] = []
    for match in _DOC_CITE_PATTERN.finditer(text):
        doc = match.group(1).strip()
        if doc and doc not in results:
            results.append(doc)
    return results
