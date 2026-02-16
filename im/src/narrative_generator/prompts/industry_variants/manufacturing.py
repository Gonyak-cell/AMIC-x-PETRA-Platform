"""제조 산업 변형 (T-N12).

> 마지막 수정: 2026-02-10 11:52:29
"""

from __future__ import annotations

from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)


class ManufacturingVariant(IndustryVariant):
    """제조업 산업 프롬프트 변형."""

    config = IndustryConfig(
        industry_id="manufacturing",
        industry_name_kr="제조",
        industry_name_en="Manufacturing",
    )

    def get_industry_context(self) -> str:
        return (
            "제조업의 IM 작성 시 다음 사항에 유의하십시오:\n"
            "- 설비 투자(CAPEX) 규모와 가동률이 수익성의 핵심 레버입니다.\n"
            "- 수율(Yield Rate) 개선과 원가 절감 노력을 수치로 입증합니다.\n"
            "- 공급망 안정성과 원자재 가격 변동 리스크를 분석합니다.\n"
            "- 감가상각비 비중이 높으므로 EBITDA가 영업이익보다 적합한 수익성 지표입니다.\n"
            "- 재고 회전율과 운전자본 관리 효율성이 현금흐름에 직결됩니다.\n"
        )

    def get_terminology_overrides(self) -> dict[str, str]:
        return {
            "매출": "출하액/매출액",
            "고객": "OEM/Tier 1 고객사",
            "시장점유율": "시장점유율 (출하 기준/매출 기준)",
            "R&D": "R&D 및 공정 개선 투자",
        }

    def get_emphasis_areas(self) -> list[str]:
        return [
            "설비 투자(CAPEX) 현황 및 계획",
            "가동률(Capacity Utilization) 및 증설 계획",
            "수율(Yield Rate) 및 품질 관리 체계",
            "공급망(Supply Chain) 안정성 및 다변화",
            "원자재 가격 변동에 대한 전가(Pass-through) 능력",
            "재고 관리 효율성 (재고 회전율, 적정 재고 수준)",
        ]
