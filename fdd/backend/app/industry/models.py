"""FDD 산업 모듈 데이터 모델.

FDD 도메인에 특화된 산업 컨텍스트 데이터 클래스.
IM의 IndustryKPI/IndustryContext 패턴을 FDD 분석 규칙 중심으로 재설계.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class FDDAdjustmentRule:
    """산업별 EBITDA 조정 규칙.

    Attributes:
        rule_id: 규칙 식별자.
        category: 조정 카테고리 (NON_RECURRING, NORMALIZATION, OPERATING, UNCLEAR).
        keywords: 감지용 키워드 목록 (한/영).
        description_kr: 한국어 설명.
        description_en: 영문 설명.
        default_confidence: 기본 신뢰도 (0~100).
        direction: 조정 방향 ("ADD_BACK" 또는 "DEDUCT").
    """

    rule_id: str
    category: str
    keywords: list[str]
    description_kr: str
    description_en: str
    default_confidence: Decimal
    direction: str


@dataclass(frozen=True)
class FDDNWCNorm:
    """산업별 NWC 정상 범위.

    Attributes:
        norm_id: 정상범위 식별자.
        description: 설명.
        typical_nwc_days: NWC 일수 정상 범위 (low, high).
        negative_nwc_acceptable: 음의 NWC 허용 여부.
        seasonal_pattern: 계절성 패턴 (None이면 없음).
        key_categories: 해당 산업에서 중요한 BS 카테고리.
    """

    norm_id: str
    description: str
    typical_nwc_days: tuple[int, int]
    negative_nwc_acceptable: bool
    seasonal_pattern: str | None
    key_categories: list[str]


@dataclass(frozen=True)
class FDDDebtClassification:
    """산업별 부채 분류 규칙.

    Attributes:
        rule_id: 규칙 식별자.
        description: 설명.
        additional_debt_like_keywords: 추가 debt-like 키워드.
        additional_cash_like_keywords: 추가 cash-like 키워드.
        special_treatments: 특수 처리 항목 {category: treatment_note}.
    """

    rule_id: str
    description: str
    additional_debt_like_keywords: list[str]
    additional_cash_like_keywords: list[str]
    special_treatments: dict[str, str]


@dataclass(frozen=True)
class FDDKPIBenchmark:
    """산업별 KPI 벤치마크.

    Attributes:
        kpi_id: KPI 식별자.
        name_kr: 한국어 KPI명.
        name_en: 영문 KPI명.
        unit: 단위 (%, x, days 등).
        benchmark_range: 벤치마크 범위 (low, high).
        formula: 산출 공식.
        higher_is_better: 높을수록 좋은 지표인지.
    """

    kpi_id: str
    name_kr: str
    name_en: str
    unit: str
    benchmark_range: tuple[float, float]
    formula: str
    higher_is_better: bool


@dataclass(frozen=True)
class FDDNarrativeTemplate:
    """산업별 내러티브 템플릿 오버라이드.

    Attributes:
        section_id: 섹션 식별자.
        template_text: Jinja2 템플릿 텍스트.
        emphasis_areas: 강조 영역.
        terminology_overrides: 용어 오버라이드 {일반 용어: 산업 용어}.
    """

    section_id: str
    template_text: str
    emphasis_areas: list[str]
    terminology_overrides: dict[str, str]


@dataclass
class FDDIndustryContext:
    """FDD 산업 컨텍스트 집계 객체.

    분석 엔진과 보고서 생성에 전달되는 통합 컨텍스트.

    Attributes:
        industry_id: 산업 식별자.
        industry_name_kr: 한국어 산업명.
        industry_name_en: 영문 산업명.
        adjustment_rules: EBITDA 조정 규칙 목록.
        nwc_norms: NWC 정상범위 목록.
        debt_classifications: 부채 분류 규칙 목록.
        kpi_benchmarks: KPI 벤치마크 목록.
        narrative_templates: 내러티브 템플릿 오버라이드.
        extra: 확장 데이터.
    """

    industry_id: str
    industry_name_kr: str
    industry_name_en: str
    adjustment_rules: list[FDDAdjustmentRule]
    nwc_norms: list[FDDNWCNorm]
    debt_classifications: list[FDDDebtClassification]
    kpi_benchmarks: list[FDDKPIBenchmark]
    narrative_templates: list[FDDNarrativeTemplate] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
