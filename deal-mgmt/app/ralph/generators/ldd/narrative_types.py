"""LDD 6블록 서술(Narrative) 타입 정의."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class NarrativeBlockType(enum.StrEnum):
    """6블록 서술 유형."""
    FACTS = "FACTS"                     # 블록 1: 사실관계
    LEGAL_REVIEW = "LEGAL_REVIEW"       # 블록 2: 법률 검토
    ANALYSIS = "ANALYSIS"               # 블록 3: 분석/해석
    DEAL_IMPACT = "DEAL_IMPACT"         # 블록 4: 거래 영향
    PENALTY = "PENALTY"                 # 블록 5: 제재/벌칙
    RECOMMENDATION = "RECOMMENDATION"   # 블록 6: 권고사항


@dataclass
class NarrativeBlock:
    """서술 블록 하나."""
    block_type: NarrativeBlockType
    title: str
    content: str = ""
    word_count: int = 0  # 실제로는 문자 수(char count). 기존 호환성 유지를 위해 필드명 유지.


@dataclass
class NarrativeResult:
    """항목 하나에 대한 전체 서술 결과."""
    item_id: str
    item_name: str
    section_type: str
    blocks: list[NarrativeBlock] = field(default_factory=list)
    total_chars: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """JSON 직렬화용 dict 변환."""
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "section_type": self.section_type,
            "blocks": [
                {
                    "block_type": b.block_type.value,
                    "title": b.title,
                    "content": b.content,
                    "word_count": b.word_count,
                }
                for b in self.blocks
            ],
            "total_chars": self.total_chars,
            "cost_usd": self.cost_usd,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NarrativeResult:
        """dict에서 NarrativeResult를 복원."""
        blocks = []
        for b in data.get("blocks", []):
            blocks.append(NarrativeBlock(
                block_type=NarrativeBlockType(b["block_type"]),
                title=b["title"],
                content=b.get("content", ""),
                word_count=b.get("word_count", 0),
            ))
        return cls(
            item_id=data["item_id"],
            item_name=data["item_name"],
            section_type=data["section_type"],
            blocks=blocks,
            total_chars=data.get("total_chars", 0),
            cost_usd=data.get("cost_usd", 0.0),
        )


# ── 블록 생성 전략 (비용 최적화) ─────────────────────────────────────────────

# issue_level → 생성할 블록 목록
BLOCK_STRATEGY: dict[str | None, list[NarrativeBlockType]] = {
    # CRITICAL/HIGH: 6블록 전체
    "CRITICAL": [
        NarrativeBlockType.FACTS,
        NarrativeBlockType.LEGAL_REVIEW,
        NarrativeBlockType.ANALYSIS,
        NarrativeBlockType.DEAL_IMPACT,
        NarrativeBlockType.PENALTY,
        NarrativeBlockType.RECOMMENDATION,
    ],
    "HIGH": [
        NarrativeBlockType.FACTS,
        NarrativeBlockType.LEGAL_REVIEW,
        NarrativeBlockType.ANALYSIS,
        NarrativeBlockType.DEAL_IMPACT,
        NarrativeBlockType.PENALTY,
        NarrativeBlockType.RECOMMENDATION,
    ],
    # MEDIUM/LOW: 4블록 (PENALTY/RECOMMENDATION 축소)
    "MEDIUM": [
        NarrativeBlockType.FACTS,
        NarrativeBlockType.LEGAL_REVIEW,
        NarrativeBlockType.ANALYSIS,
        NarrativeBlockType.RECOMMENDATION,
    ],
    "LOW": [
        NarrativeBlockType.FACTS,
        NarrativeBlockType.LEGAL_REVIEW,
        NarrativeBlockType.ANALYSIS,
        NarrativeBlockType.RECOMMENDATION,
    ],
    # OK: FACTS만
    None: [
        NarrativeBlockType.FACTS,
    ],
}


def get_blocks_for_item(status: str, issue_level: str | None) -> list[NarrativeBlockType]:
    """항목 상태에 따라 생성할 블록 목록을 반환한다.

    비용 최적화:
    - ISSUE(CRITICAL/HIGH): 6블록 전체 ($0.15-0.25)
    - ISSUE(MEDIUM/LOW): 4블록 ($0.10-0.15)
    - OK: 1블록 FACTS만 ($0.03-0.05)
    - NA/PENDING: 빈 리스트 ($0)
    """
    if status in ("NA", "PENDING"):
        return []
    if status == "OK":
        return BLOCK_STRATEGY[None]
    if status == "ISSUE" and issue_level:
        return BLOCK_STRATEGY.get(issue_level, BLOCK_STRATEGY[None])
    return BLOCK_STRATEGY[None]
