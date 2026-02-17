"""FDD 산업 모듈 추상 기반 클래스.

모든 FDD 산업 모듈은 FDDIndustryModule을 상속하며,
get_adjustment_rules(), get_nwc_norms(), get_debt_classifications(),
get_kpi_benchmarks()를 구현한다.

IM의 IndustryModule 패턴을 FDD 분석 도메인에 맞게 재설계.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.industry.korea.models import FDDKoreaOverlayData

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

    def format_narrative_context(self, section_id: str | None = None) -> str:
        """산업별 프롬프트 컨텍스트를 포맷팅된 문자열로 반환한다.

        Args:
            section_id: 특정 섹션만 필터링 (None이면 전체)

        Returns:
            LLM 시스템 프롬프트에 삽입할 산업 컨텍스트 문자열.
            템플릿이 없으면 빈 문자열.
        """
        templates = self.get_narrative_templates()
        if not templates:
            return ""
        if section_id:
            templates = [t for t in templates if t.section_id == section_id]
        if not templates:
            return ""

        parts = [f"### {self.industry_name_en} ({self.industry_name_kr}) 산업 분석 가이드\n"]
        for tmpl in templates:
            if tmpl.emphasis_areas:
                parts.append("#### 핵심 분석 영역")
                for area in tmpl.emphasis_areas:
                    parts.append(f"- {area}")
            if tmpl.terminology_overrides:
                parts.append("\n#### 산업 특화 용어")
                for general, specific in tmpl.terminology_overrides.items():
                    parts.append(f"- {general} -> {specific}")
            if tmpl.template_text:
                parts.append(f"\n#### 추가 지침\n{tmpl.template_text}")
        return "\n".join(parts)

    def get_korea_overlay(self) -> FDDKoreaOverlayData | None:
        """한국 PE FDD 특수성 오버레이 데이터를 반환한다.

        Returns:
            FDDKoreaOverlayData 인스턴스. 데이터가 없으면 None.
        """
        try:
            from app.industry.korea import get_fdd_korea_overlay_data

            return get_fdd_korea_overlay_data(self.industry_id)
        except ImportError:
            return None

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
