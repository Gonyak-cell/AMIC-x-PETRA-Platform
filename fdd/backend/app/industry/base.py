"""FDD 산업 모듈 추상 기반 클래스.

모든 FDD 산업 모듈은 FDDIndustryModule을 상속하며,
get_adjustment_rules(), get_nwc_norms(), get_debt_classifications(),
get_kpi_benchmarks()를 구현한다.

IM의 IndustryModule 패턴을 FDD 분석 도메인에 맞게 재설계.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.industry.models import (
    FDDAdjustmentRule,
    FDDDebtClassification,
    FDDIndustryContext,
    FDDKPIBenchmark,
    FDDNarrativeTemplate,
    FDDNWCNorm,
)


class FDDIndustryModule(ABC):
    """FDD 산업 모듈 추상 기반 클래스.

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
    def get_adjustment_rules(self) -> list[FDDAdjustmentRule]:
        """산업별 EBITDA 조정 규칙을 반환한다.

        Returns:
            FDDAdjustmentRule 리스트.
        """

    @abstractmethod
    def get_nwc_norms(self) -> list[FDDNWCNorm]:
        """산업별 NWC 정상 범위를 반환한다.

        Returns:
            FDDNWCNorm 리스트.
        """

    @abstractmethod
    def get_debt_classifications(self) -> list[FDDDebtClassification]:
        """산업별 부채 분류 규칙을 반환한다.

        Returns:
            FDDDebtClassification 리스트.
        """

    @abstractmethod
    def get_kpi_benchmarks(self) -> list[FDDKPIBenchmark]:
        """산업별 KPI 벤치마크를 반환한다.

        Returns:
            FDDKPIBenchmark 리스트.
        """

    def get_narrative_templates(self) -> list[FDDNarrativeTemplate]:
        """산업별 내러티브 템플릿 오버라이드를 반환한다.

        기본 구현은 빈 리스트. 산업별로 오버라이드 가능.

        Returns:
            FDDNarrativeTemplate 리스트.
        """
        return []

    def get_context(self) -> FDDIndustryContext:
        """산업 컨텍스트 요약 객체를 반환한다.

        Returns:
            FDDIndustryContext 인스턴스.
        """
        return FDDIndustryContext(
            industry_id=self.industry_id,
            industry_name_kr=self.industry_name_kr,
            industry_name_en=self.industry_name_en,
            adjustment_rules=self.get_adjustment_rules(),
            nwc_norms=self.get_nwc_norms(),
            debt_classifications=self.get_debt_classifications(),
            kpi_benchmarks=self.get_kpi_benchmarks(),
            narrative_templates=self.get_narrative_templates(),
        )
