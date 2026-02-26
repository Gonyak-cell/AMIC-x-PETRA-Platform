"""DDRL 10개 섹션 → 법무법인 8개 목차(I~VIII) 매핑.

법무법인 표준 양식의 대목차 구조:
    I.   대상사업 일반 및 거래구조
    II.  인허가 및 법령준수
    III. 계약
    IV.  부동산 및 자산
    V.   환경
    VI.  인사 및 노무
    VII. 보험
    VIII.소송 및 분쟁

DDRL 섹션(10개) → 법무법인 목차(8개)로 재배치하며,
섹션 내 항목은 원본 순서를 유지한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ─── 상수 ────────────────────────────────────────────────────────────────────

ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


@dataclass
class LawFirmChapter:
    """법무법인 목차 단일 챕터."""

    number: str          # "I", "II", ...
    title: str           # "대상사업 일반 및 거래구조"
    ddrl_sections: list[str]  # 매핑된 DDRL 섹션 타입 목록
    items: list[dict[str, Any]] = field(default_factory=list)
    narratives: list[dict[str, Any]] = field(default_factory=list)


# DDRL 섹션 → 법무법인 챕터 매핑 정의
# 한 DDRL 섹션이 여러 챕터로 분할될 수 있음 (예: REAL_ESTATE → IV + V)
CHAPTER_DEFINITIONS: list[dict[str, Any]] = [
    {
        "number": "I",
        "title": "대상사업 일반 및 거래구조",
        "ddrl_sections": ["GOVERNANCE", "CAPITAL"],
    },
    {
        "number": "II",
        "title": "인허가 및 법령준수",
        "ddrl_sections": ["PERMITS", "TAX", "DATA_IT"],
    },
    {
        "number": "III",
        "title": "계약",
        "ddrl_sections": ["CONTRACTS", "IP"],
    },
    {
        "number": "IV",
        "title": "부동산 및 자산",
        "ddrl_sections": ["REAL_ESTATE"],
        "item_filter": lambda item_id: not item_id.startswith("RE-04") and not item_id.startswith("RE-05"),
    },
    {
        "number": "V",
        "title": "환경",
        "ddrl_sections": ["REAL_ESTATE"],
        "item_filter": lambda item_id: item_id.startswith("RE-04") or item_id.startswith("RE-05"),
    },
    {
        "number": "VI",
        "title": "인사 및 노무",
        "ddrl_sections": ["LABOR"],
    },
    {
        "number": "VII",
        "title": "보험",
        "ddrl_sections": [],  # 별도 INSURANCE 항목이 있는 경우만 활성화
    },
    {
        "number": "VIII",
        "title": "소송 및 분쟁",
        "ddrl_sections": ["LITIGATION"],
    },
]


class LawFirmMapper:
    """DDRL 10개 섹션 분석 결과를 법무법인 8개 목차로 재배치.

    사용법:
        mapper = LawFirmMapper()
        chapters = mapper.map_sections(section_results, narrative_sections)
    """

    def __init__(self) -> None:
        self._chapter_defs = CHAPTER_DEFINITIONS

    def map_sections(
        self,
        section_results: dict[str, list[dict[str, Any]]],
        narrative_sections: dict[str, list[dict]] | None = None,
    ) -> list[LawFirmChapter]:
        """DDRL 분석 결과를 법무법인 목차 구조로 변환.

        Args:
            section_results: DDRL 10개 섹션별 항목 리스트 (Stage 1~2 결과)
            narrative_sections: 6블록 서술 결과 (Stage 6 결과, optional)

        Returns:
            법무법인 8개 챕터 리스트
        """
        narrative_sections = narrative_sections or {}
        chapters: list[LawFirmChapter] = []

        for ch_def in self._chapter_defs:
            chapter = LawFirmChapter(
                number=ch_def["number"],
                title=ch_def["title"],
                ddrl_sections=ch_def["ddrl_sections"],
            )

            item_filter = ch_def.get("item_filter")

            for ddrl_section in ch_def["ddrl_sections"]:
                items = section_results.get(ddrl_section, [])
                narrs = narrative_sections.get(ddrl_section, [])

                if item_filter:
                    items = [
                        it for it in items
                        if item_filter(it.get("item_id", ""))
                    ]
                    narrs = [
                        n for n in narrs
                        if item_filter(n.get("item_id", ""))
                    ]

                chapter.items.extend(items)
                chapter.narratives.extend(narrs)

            chapters.append(chapter)

        # VII. 보험 — 별도 처리: CONTRACTS 섹션 내 보험 관련 항목 수집
        insurance_chapter = chapters[6]  # VII
        if not insurance_chapter.items:
            for ddrl_section, items in section_results.items():
                for item in items:
                    name = item.get("name", "").lower()
                    item_id = item.get("item_id", "").upper()
                    if "보험" in name or "insurance" in name or "INS" in item_id:
                        insurance_chapter.items.append(item)

        logger.info(
            "법무법인 목차 매핑 완료: %s",
            ", ".join(
                f"{ch.number}.{ch.title}({len(ch.items)}항목)"
                for ch in chapters
            ),
        )

        return chapters

    def build_toc_data(self, chapters: list[LawFirmChapter]) -> dict[str, Any]:
        """목차 데이터를 JSON 직렬화 가능한 형태로 반환.

        LDDReport.law_firm_toc JSONB에 저장.
        """
        return {
            "chapters": [
                {
                    "number": ch.number,
                    "title": ch.title,
                    "ddrl_sections": ch.ddrl_sections,
                    "item_count": len(ch.items),
                    "issue_count": sum(
                        1 for it in ch.items if it.get("status") == "ISSUE"
                    ),
                    "items": [
                        {
                            "item_id": it.get("item_id", ""),
                            "name": it.get("name", ""),
                            "status": it.get("status", "PENDING"),
                            "issue_level": it.get("issue_level"),
                            "risk_color": it.get("risk_color", "GREEN"),
                        }
                        for it in ch.items
                    ],
                }
                for ch in chapters
            ],
            "total_chapters": len(chapters),
            "total_items": sum(len(ch.items) for ch in chapters),
        }
