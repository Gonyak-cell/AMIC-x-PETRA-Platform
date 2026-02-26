"""LDD 거래유형별 템플릿 기반 타입 및 추상 클래스."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ItemDef:
    """DDRL 체크리스트 항목 정의."""

    item_id: str
    name: str


@dataclass
class SectionDef:
    """LDD 보고서 섹션 정의."""

    section_type: str
    title: str
    items: list[ItemDef] = field(default_factory=list)

    def to_dict(self) -> dict:
        """DEFAULT_LDD_SECTIONS 호환 dict로 변환."""
        return {
            "section_type": self.section_type,
            "title": self.title,
            "items": [
                {
                    "item_id": item.item_id,
                    "name": item.name,
                    "status": "PENDING",
                    "issue_level": None,
                    "risk_color": "",
                    "description": "",
                    "deal_impact": "",
                    "recommendation": "",
                    "rfi_required": False,
                    "rfi_number": "",
                    "confidence": 0.0,
                    "evidence_refs": [],
                    "user_comment": "",
                    "user_approved": None,
                    "user_override_status": None,
                    "user_override_level": None,
                }
                for item in self.items
            ],
        }


@dataclass
class AppendixDef:
    """별첨 정의 (Phase 4에서 활용)."""

    appendix_id: str
    title: str
    columns: list[str] = field(default_factory=list)
    description: str = ""


class LDDTemplate:
    """거래유형별 LDD 보고서 템플릿.

    각 거래유형 서브클래스는 sections와 appendices를 정의한다.
    """

    deal_type: str = ""
    display_name: str = ""
    sections: list[SectionDef] = []
    appendices: list[AppendixDef] = []

    def get_sections_dict(self) -> list[dict]:
        """DEFAULT_LDD_SECTIONS 호환 dict 리스트 반환."""
        return [s.to_dict() for s in self.sections]

    def get_section_types(self) -> list[str]:
        """섹션 타입 목록 반환."""
        return [s.section_type for s in self.sections]

    def get_item_count(self) -> int:
        """전체 항목 수 반환."""
        return sum(len(s.items) for s in self.sections)

    def get_section_by_type(self, section_type: str) -> SectionDef | None:
        """섹션 타입으로 섹션 정의 조회."""
        for s in self.sections:
            if s.section_type == section_type:
                return s
        return None
