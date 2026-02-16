"""Korea Overlay 데이터 모델.

> 마지막 수정: 2026-02-11 15:00:00

RegulatoryItem, KIFRSNote, LaborItem, ESGRequirement, KoreaOverlayData 정의.
한국 PE 딜의 규제, K-IFRS 조정, 노동법, ESG 공시 데이터를 표현한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """규제 심각도 등급."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ESGFramework(str, Enum):
    """ESG 프레임워크 분류."""

    KCGS = "KCGS"
    TCFD = "TCFD"
    K_TAXONOMY = "K-Taxonomy"
    CSRD = "CSRD"


@dataclass(frozen=True)
class RegulatoryItem:
    """한국 규제 항목.

    Attributes:
        regulation_id: 고유 식별자 (예: "mrfta_merger").
        law_name_kr: 법률 한국어명 (예: "독점규제 및 공정거래에 관한 법률").
        law_name_en: 법률 영문명.
        authority: 관할 기관 (예: "공정거래위원회").
        description: 규제 내용 요약.
        deal_impact: M&A 딜 영향 설명.
        applicable_industries: 적용 산업 ID 목록.
        severity: 규제 심각도.
        key_articles: 주요 조항 목록.
    """

    regulation_id: str
    law_name_kr: str
    law_name_en: str
    authority: str
    description: str
    deal_impact: str
    applicable_industries: list[str] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    key_articles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class KIFRSNote:
    """K-IFRS 조정 사항.

    Attributes:
        note_id: 고유 식별자 (예: "kifrs_1115").
        standard_number: K-IFRS 기준서 번호 (예: "1115").
        topic_kr: 주제 한국어명.
        topic_en: 주제 영문명.
        description: K-IFRS 요점 설명.
        deal_consideration: DD/딜 시 고려사항.
        applicable_industries: 적용 산업 ID 목록.
    """

    note_id: str
    standard_number: str
    topic_kr: str
    topic_en: str
    description: str
    deal_consideration: str
    applicable_industries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LaborItem:
    """한국 노동법 준수 항목.

    Attributes:
        labor_id: 고유 식별자 (예: "labor_standard_act").
        law_name_kr: 법률 한국어명.
        law_name_en: 법률 영문명.
        description: 내용 요약.
        deal_impact: M&A 딜 영향 설명.
        applicable_industries: 적용 산업 ID 목록.
    """

    labor_id: str
    law_name_kr: str
    law_name_en: str
    description: str
    deal_impact: str
    applicable_industries: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ESGRequirement:
    """ESG 공시 요구사항.

    Attributes:
        esg_id: 고유 식별자 (예: "kcgs_governance").
        framework: ESG 프레임워크.
        category: 분류 (예: "지배구조", "환경", "사회").
        description: 요구사항 설명.
        mandatory: 의무 공시 여부.
        applicable_industries: 적용 산업 ID 목록.
        effective_year: 시행 연도.
    """

    esg_id: str
    framework: ESGFramework
    category: str
    description: str
    mandatory: bool = False
    applicable_industries: list[str] = field(default_factory=list)
    effective_year: int | None = None


@dataclass
class KoreaOverlayData:
    """한국 오버레이 데이터 집계 컨테이너.

    Attributes:
        industry_id: 산업 식별자.
        regulatory_items: 해당 산업 규제 항목 리스트.
        kifrs_notes: K-IFRS 조정사항 리스트.
        labor_items: 노동법 항목 리스트.
        esg_requirements: ESG 요구사항 리스트.
    """

    industry_id: str = ""
    regulatory_items: list[RegulatoryItem] = field(default_factory=list)
    kifrs_notes: list[KIFRSNote] = field(default_factory=list)
    labor_items: list[LaborItem] = field(default_factory=list)
    esg_requirements: list[ESGRequirement] = field(default_factory=list)
