"""일반(General) 산업 변형.

> 마지막 수정: 2026-02-12 10:39:21

산업 비특화 기업에 대한 범용 재무분석 프롬프트 가이드를 제공한다.
"""

from __future__ import annotations

from src.narrative_generator.prompts.industry_variants.base_variant import (
    IndustryConfig,
    IndustryVariant,
)


class GeneralVariant(IndustryVariant):
    """범용 산업 프롬프트 변형.

    산업 비특화 기업에 대해 기본 재무분석 프레임워크를 적용한다.
    """

    config = IndustryConfig(
        industry_id="general",
        industry_name_kr="일반",
        industry_name_en="General",
    )

    def get_industry_context(self) -> str:
        return (
            "이 기업은 특정 산업 분류가 지정되지 않았습니다.\n"
            "범용 재무 분석 프레임워크를 적용하여 IM을 작성하십시오:\n"
            "- 매출 성장률, 영업이익률, EBITDA 마진 등 기본 수익성 지표를 분석합니다.\n"
            "- 부채비율, 유동비율 등 재무 건전성을 평가합니다.\n"
            "- 잉여현금흐름(FCF) 기반 가치평가 관점을 포함합니다.\n"
            "- ROE 분석을 통해 자본 효율성을 평가합니다.\n"
        )

    def get_terminology_overrides(self) -> dict[str, str]:
        return {}

    def get_emphasis_areas(self) -> list[str]:
        return [
            "매출 성장 추이 및 성장 동인",
            "영업이익률·EBITDA 마진 추이",
            "자기자본이익률(ROE) 및 자본 효율성",
            "부채 구조 및 재무 건전성",
            "잉여현금흐름(FCF) 창출 능력",
        ]
