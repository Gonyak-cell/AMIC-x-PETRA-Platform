"""FDD Korea Overlay 데이터 모델.

FDD(Financial Due Diligence) 관점의 한국 특수성 데이터 클래스.
IM의 KoreaOverlayData 패턴을 FDD 도메인(EBITDA 조정, NWC, Net Debt)에 맞게 재설계.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """규제/세무 영향도 등급."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class FDDRegulatoryItem:
    """FDD 관점 한국 규제 항목.

    Attributes:
        regulation_id: 고유 식별자 (예: "merger_review").
        law_name_kr: 법률 한국어명.
        authority: 관할 기관.
        fdd_impact: FDD 분석 영향 (EBITDA/NWC/Net Debt 관점).
        applicable_industries: 적용 산업 ID 목록.
        severity: 영향도 등급.
        key_articles: 주요 조항 목록.
    """

    regulation_id: str
    law_name_kr: str
    authority: str
    fdd_impact: str
    applicable_industries: list[str] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    key_articles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FDDKIFRSNote:
    """FDD 관점 K-IFRS 조정 사항.

    Attributes:
        standard_number: K-IFRS 기준서 번호 (예: "1115").
        topic_kr: 주제 한국어명.
        ebitda_impact: EBITDA 조정 관련성 설명.
        nwc_impact: NWC 산정 관련성 설명.
        net_debt_impact: Net Debt 산정 관련성 설명.
        applicable_industries: 적용 산업 ID 목록.
    """

    standard_number: str
    topic_kr: str
    ebitda_impact: str
    nwc_impact: str
    net_debt_impact: str = ""
    applicable_industries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FDDTaxItem:
    """FDD 관점 한국 세무 검토 사항.

    Attributes:
        item_id: 고유 식별자 (예: "transfer_pricing").
        description_kr: 세무 항목 설명.
        fdd_consideration: FDD 세무 검토 시 고려사항.
        applicable_industries: 적용 산업 ID 목록.
        severity: 영향도 등급.
    """

    item_id: str
    description_kr: str
    fdd_consideration: str
    applicable_industries: list[str] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM


@dataclass
class FDDKoreaOverlayData:
    """FDD 한국 오버레이 데이터 집계 컨테이너.

    Attributes:
        industry_id: 산업 식별자.
        regulatory_items: 해당 산업 규제 항목.
        kifrs_notes: K-IFRS 조정사항.
        tax_items: 세무 검토 사항.
    """

    industry_id: str = ""
    regulatory_items: list[FDDRegulatoryItem] = field(default_factory=list)
    kifrs_notes: list[FDDKIFRSNote] = field(default_factory=list)
    tax_items: list[FDDTaxItem] = field(default_factory=list)

    def format_overlay_context(self) -> str:
        """한국 오버레이 데이터를 LLM 프롬프트용 문자열로 포맷팅한다."""
        if not any([self.regulatory_items, self.kifrs_notes, self.tax_items]):
            return ""

        parts = ["### 한국 PE FDD 특수 고려사항\n"]

        if self.kifrs_notes:
            parts.append("#### K-IFRS 조정 사항")
            for note in self.kifrs_notes:
                parts.append(f"- **K-IFRS {note.standard_number} ({note.topic_kr})**")
                if note.ebitda_impact:
                    parts.append(f"  - EBITDA 영향: {note.ebitda_impact}")
                if note.nwc_impact:
                    parts.append(f"  - NWC 영향: {note.nwc_impact}")
                if note.net_debt_impact:
                    parts.append(f"  - Net Debt 영향: {note.net_debt_impact}")

        if self.regulatory_items:
            parts.append("\n#### 규제 검토 사항")
            for reg in self.regulatory_items:
                parts.append(f"- **{reg.law_name_kr}** ({reg.authority})")
                parts.append(f"  - FDD 영향: {reg.fdd_impact}")

        if self.tax_items:
            parts.append("\n#### 세무 검토 사항")
            for tax in self.tax_items:
                parts.append(f"- **{tax.description_kr}**")
                parts.append(f"  - 검토 사항: {tax.fdd_consideration}")

        return "\n".join(parts)
