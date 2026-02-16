"""산업 모듈 추상 기반 클래스.

> 마지막 수정: 2026-02-11 15:00:00

모든 산업 모듈은 IndustryModule을 상속하며,
get_kpis(), get_financial_weights(), get_chart_recommendations(),
get_narrative_variant()를 구현한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.industry.models import (
    IndustryChartRecommendation,
    IndustryContext,
    IndustryKPI,
    RiskCategory,
)

if TYPE_CHECKING:
    from src.industry.korea.models import KoreaOverlayData
    from src.narrative_generator.prompts.industry_variants.base_variant import (
        IndustryVariant,
    )


class IndustryModule(ABC):
    """산업 모듈 추상 기반 클래스.

    각 산업 모듈은 industry_id, industry_name_kr, industry_name_en
    클래스 변수를 선언하고, 4개 추상 메서드를 구현한다.

    Attributes:
        industry_id: 산업 식별자 (예: "tech", "manufacturing").
        industry_name_kr: 한국어 산업명.
        industry_name_en: 영문 산업명.
    """

    industry_id: str
    industry_name_kr: str
    industry_name_en: str

    @abstractmethod
    def get_kpis(self) -> list[IndustryKPI]:
        """산업별 핵심 KPI 정의를 반환한다.

        Returns:
            IndustryKPI 리스트.
        """

    @abstractmethod
    def get_financial_weights(self) -> dict[str, float]:
        """산업별 재무 지표 가중치를 반환한다.

        Returns:
            {지표명: 가중치(0.0~1.0)} 딕셔너리.
        """

    @abstractmethod
    def get_chart_recommendations(self) -> list[IndustryChartRecommendation]:
        """산업별 추천 차트 사양을 반환한다.

        Returns:
            IndustryChartRecommendation 리스트.
        """

    @abstractmethod
    def get_narrative_variant(self) -> IndustryVariant:
        """기존 내러티브 변형 객체를 반환한다.

        Returns:
            IndustryVariant 인스턴스.
        """

    def get_risk_categories(self) -> list[RiskCategory]:
        """산업별 리스크 카테고리를 반환한다.

        기본 구현은 빈 리스트. 산업별로 오버라이드 가능.

        Returns:
            RiskCategory 리스트.
        """
        return []

    def get_context(self) -> IndustryContext:
        """산업 컨텍스트 요약 객체를 반환한다.

        Returns:
            IndustryContext 인스턴스.
        """
        return IndustryContext(
            industry_id=self.industry_id,
            industry_name_kr=self.industry_name_kr,
            industry_name_en=self.industry_name_en,
            kpis=self.get_kpis(),
            financial_weights=self.get_financial_weights(),
            chart_recommendations=self.get_chart_recommendations(),
            risk_categories=self.get_risk_categories(),
        )

    def get_korea_overlay(self) -> KoreaOverlayData | None:
        """한국 PE 특수성 오버레이 데이터를 반환한다.

        산업별 규제, K-IFRS 조정사항, 노동법, ESG 요구사항을 집계.
        한국 오버레이 모듈이 로드되지 않거나 해당 산업 데이터가 없으면 None.

        Returns:
            KoreaOverlayData 인스턴스 또는 None.
        """
        try:
            from src.industry.korea import get_korea_overlay_data

            return get_korea_overlay_data(self.industry_id)
        except ImportError:
            return None
