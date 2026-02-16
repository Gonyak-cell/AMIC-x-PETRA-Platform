"""산업 모듈 데이터 모델.

> 마지막 수정: 2026-02-11 10:00:00

IndustryKPI, IndustryContext, IndustryChartRecommendation, RiskCategory
데이터클래스를 정의한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class KPIUnit(str, Enum):
    """KPI 단위."""

    PERCENTAGE = "%"
    RATIO = "x"
    CURRENCY_KRW = "억원"
    CURRENCY_USD = "$M"
    COUNT = "건"
    DAYS = "일"
    RATE = "회"
    CUSTOM = ""


@dataclass(frozen=True)
class IndustryKPI:
    """산업별 핵심 KPI 정의.

    Attributes:
        kpi_id: KPI 고유 식별자 (예: "arr", "nrr", "oee").
        name_kr: 한국어 KPI명.
        name_en: 영문 KPI명.
        unit: KPI 단위.
        description: KPI 설명 (한국어).
        formula: 계산 공식 설명 (선택적).
        display_format: 표시 포맷 문자열 (예: "{:,.0f}억원", "{:.1f}%").
        higher_is_better: True면 값이 클수록 긍정적.
        benchmark_range: 업계 벤치마크 범위 (하한, 상한). None이면 미설정.
    """

    kpi_id: str
    name_kr: str
    name_en: str
    unit: KPIUnit = KPIUnit.PERCENTAGE
    description: str = ""
    formula: str = ""
    display_format: str = "{:.1f}"
    higher_is_better: bool = True
    benchmark_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class IndustryChartRecommendation:
    """산업별 추천 차트 사양.

    Attributes:
        chart_type: 차트 유형 ("combo", "waterfall", "donut", "line", "hbar",
                    "stacked_bar").
        title_template: 차트 제목 템플릿 (예: "{company_name} ARR 추이").
        target_section: 차트를 배치할 섹션 ID (예: "financial_analysis").
        data_keys: 차트에 필요한 데이터 키 목록.
        priority: 우선순위 (1=최고). 공간 부족 시 낮은 우선순위 차트 생략.
        description: 차트 설명.
    """

    chart_type: str
    title_template: str
    target_section: str
    data_keys: list[str] = field(default_factory=list)
    priority: int = 1
    description: str = ""


@dataclass(frozen=True)
class RiskCategory:
    """산업별 리스크 카테고리.

    Attributes:
        category_id: 리스크 카테고리 식별자 (예: "regulatory", "supply_chain").
        name_kr: 한국어 카테고리명.
        name_en: 영문 카테고리명.
        description: 카테고리 설명.
        risk_factors: 해당 카테고리의 구체적 리스크 요인 목록.
    """

    category_id: str
    name_kr: str
    name_en: str
    description: str = ""
    risk_factors: list[str] = field(default_factory=list)


@dataclass
class IndustryContext:
    """산업 컨텍스트 요약 — IndustryModule.get_context()의 반환값.

    파이프라인에서 산업별 데이터를 일괄 전달하는 용도.

    Attributes:
        industry_id: 산업 식별자.
        industry_name_kr: 한국어 산업명.
        industry_name_en: 영문 산업명.
        kpis: 산업별 KPI 정의 리스트.
        financial_weights: 재무 지표 가중치.
        chart_recommendations: 추천 차트 사양 리스트.
        risk_categories: 리스크 카테고리 리스트.
        extra: 추가 산업별 데이터 (유연한 확장용).
    """

    industry_id: str = ""
    industry_name_kr: str = ""
    industry_name_en: str = ""
    kpis: list[IndustryKPI] = field(default_factory=list)
    financial_weights: dict[str, float] = field(default_factory=dict)
    chart_recommendations: list[IndustryChartRecommendation] = field(
        default_factory=list
    )
    risk_categories: list[RiskCategory] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
